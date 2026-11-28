"""The character select's random pick: which clones it can pick.

The game keeps the characters random can still pick as a 96-bit set in its random-pool object (+0x98, 12 bytes; the
next field starts at +0xA4, so the set can't grow in place): bit i = the database entry at position i, which is the
character id for every fighter (new ids sit at position = id). The refill 0x02FFB610 scans the first 0x51 entries
(`li r23` at 0x02FFB644, raised by the kind expansion with the new ids, at most 96), the count of picks left
0x02FFC4A8 counts bits 0-0x50 (`li r11, 0x51` at 0x02FFC4BC), and the remove 0x02FFC5BC ignores positions >= 0x51
(`cmplwi r4, 0x51` at 0x02FFC5C4).

This patch:
- raises both other bounds to the refill's scan count (min(96, 0x51 + new ids)): the clones' bits are counted and
  removed like the game's (with the bounds at 0x51, a clone with an id from 0x51 would never leave the pool);
- masks the refill's stores (0x02FFB6C4 `stwx r12, r29, r10` -> a stub: AND with an allow mask of 96 bits, then
  the store): a clone with "random": false never gets its bit.
Ids 96 and up (the 38th clone on) are past the set: never in random (the refill doesn't scan them).
"""
from . import _paths  # noqa: F401
from ppcasm import Asm, ha  # noqa: E402

STORE = 0x02FFB6C4          # stwx r12, r29, r10 (the set word, at r29 + r10)
COUNT_LOOP = 0x02FFC4BC     # li r11, 0x51
REMOVE_BOUND = 0x02FFC5C4   # cmplwi r4, 0x51
OLD = 0x51
BITS = 96
FIRST_ID = 59


def slo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def one(addr, text):
    a = Asm(addr)
    a.asm(text)
    return a.words()[0]


def scan_count(n_ids):
    return min(BITS, OLD + n_ids)


def mask_words(fighters):
    """3 words: bit i set = id i may be in the pool (every game id; clones unless "random": false)"""
    words = [0xFFFFFFFF] * 3
    for f in fighters:
        i = f['ui_id']
        if i < BITS and f.get('random', True) is False:
            words[i // 32] &= ~(1 << (i % 32)) & 0xFFFFFFFF
    return words


def build(read, fighters, cave, limit):
    """{address: word} (cave + in place) and the originals checked; read(addr) -> the view's word"""
    n = scan_count(len(fighters))
    checks = {STORE: one(STORE, 'stwx r12, r29, r10'), COUNT_LOOP: one(COUNT_LOOP, 'li r11, 0x51'),
              REMOVE_BOUND: one(REMOVE_BOUND, 'cmplwi r4, 0x51')}
    bad = ['0x%08X is 0x%08X, expected 0x%08X' % (a, read(a), w) for a, w in checks.items() if read(a) != w]
    if bad:
        raise AssertionError('random select: ' + '; '.join(bad))
    mask = cave
    code = cave + 12
    a = Asm(code)
    a.asm('''
        lis r11, 0x%X
        addi r11, r11, %d
        lwzx r11, r11, r10          # the allow mask's word for this set word
        and r12, r12, r11
        stwx r12, r29, r10
        b 0x%X''' % (ha(mask), slo(mask), STORE + 4))
    words = {mask + 4 * i: w for i, w in enumerate(mask_words(fighters))}
    words.update({code + 4 * i: w for i, w in enumerate(a.words())})
    assert code + 4 * len(a.words()) <= limit, 'random select cave full'
    b = Asm(STORE)
    b.asm('b 0x%X' % code)
    words[STORE] = b.words()[0]
    words[COUNT_LOOP] = one(COUNT_LOOP, 'li r11, %d' % n)
    words[REMOVE_BOUND] = one(REMOVE_BOUND, 'cmplwi r4, %d' % n)
    return words
