#!/usr/bin/env python3
"""Kirby's trait badge on his damage panel: shows the frame of dmg.flx's `trait_mc` element (one
frame a trait, tools/flx.py adds it) that matches the trait in his marker int, hidden
when he has no copy ability or isn't Kirby.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/trait_badge_cave.py)

Kirby's MSC (fighters/kirby/kirby.c kirby_trait_update) writes int 0x1000008E = 0x4B49xxxx every
frame, bits 8-11 the trait (0 none, 1 Normal, 2 Rush, 3 Shooter, 4 Strike, 5 Juggernaut, 6 Technical,
7 Barrage).

Native details (research: docs/flx2-format.md, docs/native-notes.md "Damage panel"):
  hook        the damage panel's per-frame update, its vtable's +0x3C (0x100871D8 + 0x3C =
              0x02661808, called by the UI manager at 0x028FA088 with r3 = panel P), is pointed at
              the cave (a data word: its load-time relocation moved to a dead word, RELOC_DUMMY), which
              calls it, then updates each slot's badge (its code is out of a branch's reach from the
              cave: the grown space is 37 MB from it)
  slot        S = P + 0xC0 + slot * 0x30C0 (8): +0 s16 entry id, +8 s16 2 = empty, +0xA s8 fighter
              kind (Kirby 8),
              +0x5C the player's panel clip, +0x60 a panel element (its alpha byte +0x74 follows the
              panel's fade)
  fighter     FM = [0x102F7024], FE = [FM + 0x24 + entry * 4] (entry < [FM + 0x18]),
              obj = [FE + 0xDC0 + 4 * lbz FE+0x14E9] (< [FE + 0xDB4]); obj +4 kind, +0xC accessor,
              accessor +0x28 WorkModule; the int is read as tools/strike_cave.py does
  flx runtime 0x032CB1B8([0x102FCAA4] + 0x24, char*, len) -> name atom (interned each frame, on
              the first slot that needs it: a cached atom went stale after a Great Cave Offensive
              match, so trait_mc wasn't found and the badges showed on every panel);
              0x032CCAA0(inst, &atom) child by instance name (0: none: a vanilla dmg.flx, nothing
              happens); 0x032CDFFC(inst, visible); 0x032CE00C(inst) frame (1-based);
              0x032CCC44(inst, frame) goto (then +0x9C = 1: stopped); 0x032CDF6C(inst, alpha)
Every pointer it follows is checked (word aligned, 0x10000000-0x8FFFFFFF); a bad one hides nothing
and changes nothing.

Hero's Command Selection window (MENU, called for each slot after the badge; fighters/brave/README.md):
dmg.flx's cmdwin_mc (the window), spell0_mc ... spell3_mc (the names: frame n = spell n, 21 + n greyed:
int 0x1000009F bit 20 + row), cmdcur0_mc ... cmdcur3_mc (the pointer, shown on the cursor's row) and
cmdmp_mc (frame n = spell n's cost, the cursor's spell) (tools/dmg_brave_menu.py) show the window of a Hero panel (its fighter object's kind 0x45; the panel slot's kind byte
isn't trusted for an added kind) while his MSC
(fighters/brave/brave.c brave_lw_*) has the menu open: int 0x1000009E = 0x4845xxxx, bit 2 open, bits
0-1 the cursor's row; int 0x1000009F = 0x48xxxxxx, the rows' spells (1-21, 0 none) in bits 0-4,
5-9, 10-14, 15-19. Otherwise (another fighter, no marker, the menu shut, a row with no spell) the rows
are hidden. The names are interned for every slot (four a slot, no cache: see the badge's atom).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402
import strike_cave  # noqa: E402

VTABLE_UPDATE = 0x100871D8 + 0x3C
UPDATE = 0x02661808            # the original
RELOC_DUMMY = 0x037EE73C       # a dead word for relocations (as position_vars_cave.py)
SLOTS = 8
CAVE = 0x04B84000
LIMIT = 0x04B84800              # grown (monster_roll_cave.py's space ends at CAVE)
SLOT_SIZE = 0x30C0
KIRBY = 8
NAME = b'trait_mc'
TRAITS = 7                      # frames 1-7
FIGHTER_MANAGER = 0x102F7024
ATOM_POOL = 0x102FCAA4
INTERN = 0x032CB1B8
FIND_CHILD = 0x032CCAA0
SET_VISIBLE = 0x032CDFFC
GET_FRAME = 0x032CE00C
GOTO_FRAME = 0x032CCC44
SET_ALPHA = 0x032CDF6C
MENU = 0x04B85000               # free grown space (kind_expand.py's old 0x04B85000-0x04B88000)
MENU_LIMIT = 0x04B85800
BRAVE = 0x45
MENU_INT, SPELL_INT = 0x9E, 0x9F
MENU_MAGIC, SPELL_MAGIC = 0x4845, 0x48
ROWS = 4
SPELLS = 21
# the window's elements (tools/dmg_brave_menu.py), in the order the routine goes through them
ELEMENTS = [b'cmdwin_mc'] + [b'spell%d_mc' % k for k in range(4)] + [b'cmdcur%d_mc' % k for k in range(4)] + \
    [b'cmdmp_mc']


def ha(v):
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def chk(reg, fail):
    return strike_cave.chk(reg, fail)


DEBUG = '--debug' in sys.argv     # count each step into the words at the `counters` label
COUNTERS = ['hook calls', 'non-empty slots', 'trait_mc found', 'slot kind is Kirby', 'Kirby fighter found',
            'last marker int', 'last trait shown', 'badge shown (count)', 'last slot kind', 'last panel clip',
            'name atom', 'last hidden slot']


def debug_expand(text):
    """the source's "#DBG n" lines (counters[n] += 1) and "#DBG n reg" (counters[n] = reg): code with
    --debug, nothing without (r8 / r9 are free everywhere they're used)"""
    out = []
    for line in text.split('\n'):
        m = re.match(r'\s*#DBG (\d+)(?: (r\d+))?$', line)
        if not m:
            out.append(line)
            continue
        if DEBUG:
            n = int(m.group(1))
            out += ['        lis r9, counters@ha', '        addi r9, r9, counters@l']
            out += ['        stw %s, %d(r9)' % (m.group(2), 4 * n)] if m.group(2) else \
                ['        lwz r8, %d(r9)' % (4 * n), '        addi r8, r8, 1', '        stw r8, %d(r9)' % (4 * n)]
    return '\n'.join(out)


def build():
    a = Asm(CAVE)
    a.asm(debug_expand("""
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r24, 0x18(r1)
        mr r31, r3
#DBG 0
        lis r12, 0x%(upd_hi)04X
        addi r12, r12, %(upd_lo)d
        mtctr r12
        bctrl
        stw r3, 0x10(r1)
        li r0, 0                    # intern the name again each frame (badge): the flx runtime's
        lis r12, atom@ha            # name table can be rebuilt (it was after a Great Cave
        stw r0, atom@l(r12)         # Offensive match: a stale atom found nothing, nothing hidden)
        li r26, 0
slots:
        cmpwi r26, %(slots)d
        bge done
        mulli r3, r26, %(slot)d
        add r3, r3, r31
        addi r3, r3, 0xC0
        lha r0, 8(r3)
        cmpwi r0, 2
        beq next
#DBG 1
        bl badge
        mulli r3, r26, %(slot)d
        add r3, r3, r31
        addi r3, r3, 0xC0
        bl 0x%(menu)08X
next:
        addi r26, r26, 1
        b slots
done:
        lwz r3, 0x10(r1)
        lmw r24, 0x18(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
badge:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x18(r1)
        mr r29, r3
        lwz r30, 0x5C(r29)
#DBG 9 r30
""" % dict(slot=SLOT_SIZE, slots=SLOTS, upd_hi=ha(UPDATE), upd_lo=lo(UPDATE), menu=MENU) + chk('r30', 'out') + """
        lis r31, atom@ha
        addi r31, r31, atom@l
        lwz r0, 0(r31)
        cmpwi r0, 0
        bne have
        lis r3, %(pool_hi)d
        lwz r3, %(pool_lo)d(r3)
""" % dict(pool_hi=ha(ATOM_POOL), pool_lo=lo(ATOM_POOL)) + chk('r3', 'out') + """
        addi r3, r3, 0x24
        lis r4, name@ha
        addi r4, r4, name@l
        li r5, %(len)d
        bl 0x%(intern)08X
        stw r3, 0(r31)
#DBG 10 r3
        cmpwi r3, 0
        beq out
have:
        mr r3, r30
        mr r4, r31
        bl 0x%(find)08X
        mr. r28, r3
        beq out
""" % dict(len=len(NAME), intern=INTERN, find=FIND_CHILD) + chk('r28', 'out') + """
#DBG 2
        li r27, 0
        lbz r0, 0xA(r29)
        extsb r0, r0
#DBG 8 r0
        cmpwi r0, %(kirby)d
        bne show
#DBG 3
        lha r5, 0(r29)
        cmpwi r5, 0
        blt show
        lis r12, %(fm_hi)d
        lwz r12, %(fm_lo)d(r12)
""" % dict(kirby=KIRBY, fm_hi=ha(FIGHTER_MANAGER), fm_lo=lo(FIGHTER_MANAGER)) + chk('r12', 'show') + """
        lwz r0, 0x18(r12)
        cmplw r5, r0
        bge show
        slwi r5, r5, 2
        add r12, r12, r5
        lwz r12, 0x24(r12)
""" + chk('r12', 'show') + """
        lbz r5, 0x14E9(r12)
        lwz r0, 0xDB4(r12)
        cmplw r5, r0
        bge show
        slwi r5, r5, 2
        add r12, r12, r5
        lwz r12, 0xDC0(r12)
""" + chk('r12', 'show') + """
        lwz r0, 4(r12)
        cmpwi r0, %(kirby)d
        bne show
#DBG 4
        lwz r12, 0xC(r12)
""" % dict(kirby=KIRBY) + chk('r12', 'show') + """
        lwz r12, 0x28(r12)
""" + chk('r12', 'show') + """
        lwz r10, 8(r12)
""" + chk('r10', 'show') + """
        lwz r11, 0(r10)
""" + chk('r11', 'show') + """
        lwz r10, 8(r11)
        rlwinm r10, r10, 0, 2, 31
        cmplwi r10, %(n)d
        blt show
        lwz r11, 0xC(r11)
""" % dict(n=strike_cave.INT_INDEX + 1) + chk('r11', 'show') + """
        lwz r11, %(off)d(r11)
#DBG 5 r11
        srwi r10, r11, 16
        cmplwi r10, %(magic)d
        bne show
        rlwinm r27, r11, 24, 28, 31
        cmplwi r27, %(traits)d
        ble show
        li r27, 0
show:
        cmpwi r27, 0
        beq hide
#DBG 6 r27
#DBG 7
        mr r3, r28
        li r4, 1
        bl 0x%(vis)08X
        mr r3, r28
        bl 0x%(getf)08X
        cmpw r3, r27
        beq alpha
        mr r3, r28
        mr r4, r27
        bl 0x%(gotof)08X
        li r0, 1
        sth r0, 0x9C(r28)
alpha:
        lwz r12, 0x60(r29)
""" % dict(off=strike_cave.INT_INDEX * 4, magic=strike_cave.MAGIC, traits=TRAITS, vis=SET_VISIBLE,
           getf=GET_FRAME, gotof=GOTO_FRAME) + chk('r12', 'out') + """
        lbz r4, 0x74(r12)
        mr r3, r28
        bl 0x%(alpha)08X
        b out
hide:
#DBG 11 r29
        mr r3, r28
        li r4, 0
        bl 0x%(vis)08X
out:
        lmw r27, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
atom:
        .word 0
name:
""" % dict(alpha=SET_ALPHA, vis=SET_VISIBLE)))
    nm = NAME + b'\0' * (4 - len(NAME) % 4)
    for i in range(0, len(nm), 4):
        a.asm('.word 0x%08X' % int.from_bytes(nm[i:i + 4], 'big'))
    if DEBUG:
        a.asm('counters:\n' + '\n'.join('        .word 0' for _ in COUNTERS))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT
    m = build_menu()
    return a, words, [(VTABLE_UPDATE, CAVE)], m


def build_menu():
    """Hero's menu rows for the panel slot in r3 (see the docstring)"""
    m = Asm(MENU)
    m.asm("""
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r24, 0x18(r1)
        mr r29, r3
        lwz r30, 0x5C(r29)
""" + chk('r30', 'mout') + """
        li r25, 0
        li r24, 0
        lha r5, 0(r29)
        cmpwi r5, 0
        blt rows
        lis r12, %(fm_hi)d
        lwz r12, %(fm_lo)d(r12)
""" % dict(fm_hi=ha(FIGHTER_MANAGER), fm_lo=lo(FIGHTER_MANAGER)) + chk('r12', 'rows') + """
        lwz r0, 0x18(r12)
        cmplw r5, r0
        bge rows
        slwi r5, r5, 2
        add r12, r12, r5
        lwz r12, 0x24(r12)
""" + chk('r12', 'rows') + """
        lbz r5, 0x14E9(r12)
        lwz r0, 0xDB4(r12)
        cmplw r5, r0
        bge rows
        slwi r5, r5, 2
        add r12, r12, r5
        lwz r12, 0xDC0(r12)
""" + chk('r12', 'rows') + """
        lwz r0, 4(r12)
        cmpwi r0, %(brave)d
        bne rows
        lwz r12, 0xC(r12)
""" % dict(brave=BRAVE) + chk('r12', 'rows') + """
        lwz r12, 0x28(r12)
""" + chk('r12', 'rows') + """
        lwz r10, 8(r12)
""" + chk('r10', 'rows') + """
        lwz r11, 0(r10)
""" + chk('r11', 'rows') + """
        lwz r10, 8(r11)
        rlwinm r10, r10, 0, 2, 31
        cmplwi r10, %(n)d
        blt rows
        lwz r11, 0xC(r11)
""" % dict(n=SPELL_INT + 1) + chk('r11', 'rows') + """
        lwz r25, %(aoff)d(r11)
        lwz r24, %(boff)d(r11)
        srwi r0, r25, 16
        cmplwi r0, %(amagic)d
        bne shut
        srwi r0, r24, 24
        cmplwi r0, %(bmagic)d
        bne shut
        andi. r0, r25, 4
        bne rows
shut:
        li r25, 0
rows:
        li r26, 0
row:
        cmpwi r26, %(nel)d
        bge mout
        lis r3, %(pool_hi)d
        lwz r3, %(pool_lo)d(r3)
""" % dict(aoff=MENU_INT * 4, boff=SPELL_INT * 4, amagic=MENU_MAGIC, bmagic=SPELL_MAGIC, nel=len(ELEMENTS),
           pool_hi=ha(ATOM_POOL), pool_lo=lo(ATOM_POOL)) + chk('r3', 'mout') + """
        addi r3, r3, 0x24
        lis r4, names@ha
        addi r4, r4, names@l
        slwi r0, r26, 4
        add r4, r4, r0
        lwz r5, 12(r4)              # the name's length (the slot's last word)
        bl 0x%(intern)08X
        stw r3, 0x10(r1)
        cmpwi r3, 0
        beq nextrow
        mr r3, r30
        addi r4, r1, 0x10
        bl 0x%(find)08X
        mr. r28, r3
        beq nextrow
""" % dict(intern=INTERN, find=FIND_CHILD) + chk('r28', 'nextrow') + """
        li r27, 0                   # the frame (0: hidden)
        cmpwi r25, 0
        beq apply
        cmpwi r26, 0
        bne notwin
        li r27, 1                   # the window
        b apply
notwin:
        cmpwi r26, 4
        bgt notrow
        addi r9, r26, -1            # spellK_mc: row K's spell, + 21 greyed (B bit 20 + K)
        bl spell
        mr r27, r3
        cmpwi r27, 0
        beq apply
        addi r0, r9, 20
        srw r0, r24, r0
        andi. r0, r0, 1
        beq apply
        addi r27, r27, %(spells)d
        b apply
notrow:
        cmpwi r26, 8
        bgt mp
        addi r9, r26, -5            # cmdcurK_mc: shown on the cursor's row (if it has a spell)
        andi. r0, r25, 3
        cmpw r0, r9
        bne apply
        bl spell
        cmpwi r3, 0
        beq apply
        li r27, 1
        b apply
mp:
        andi. r9, r25, 3            # cmdmp_mc: the cost of the cursor's spell
        bl spell
        mr r27, r3
apply:
        cmpwi r27, 0
        beq rhide
        mr r3, r28
        li r4, 1
        bl 0x%(vis)08X
        mr r3, r28
        bl 0x%(getf)08X
        cmpw r3, r27
        beq ralpha
        mr r3, r28
        mr r4, r27
        bl 0x%(gotof)08X
        li r0, 1
        sth r0, 0x9C(r28)
ralpha:
        lwz r12, 0x60(r29)
""" % dict(spells=SPELLS, vis=SET_VISIBLE, getf=GET_FRAME, gotof=GOTO_FRAME) + chk('r12', 'nextrow') + """
        lbz r4, 0x74(r12)
        mr r3, r28
        bl 0x%(alpha)08X
        b nextrow
rhide:
        mr r3, r28
        li r4, 0
        bl 0x%(vis)08X
nextrow:
        addi r26, r26, 1
        b row
mout:
        lmw r24, 0x18(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
spell:                              # r3 = row r9's spell (1-21), 0 for none (uses r0)
        mulli r0, r9, 5
        srw r3, r24, r0
        andi. r3, r3, 31
        cmplwi r3, %(spells)d
        blelr
        li r3, 0
        blr
names:
""" % dict(alpha=SET_ALPHA, vis=SET_VISIBLE, spells=SPELLS))
    for nm in ELEMENTS:                     # 16 bytes each: the name (NUL-padded, 12) and its length
        assert len(nm) < 12
        b = nm.ljust(12, b'\0')
        for i in range(0, 12, 4):
            m.asm('.word 0x%08X' % int.from_bytes(b[i:i + 4], 'big'))
        m.asm('.word %d' % len(nm))
    words = m.words()
    assert MENU + 4 * len(words) <= MENU_LIMIT
    return words


def main():
    a, words, hooks, menu = build()
    out = ['grow:0x%08X' % MENU_LIMIT, 'reloc:0x%08X-0x%08X=0x%08X' % (VTABLE_UPDATE, VTABLE_UPDATE + 4, RELOC_DUMMY)]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (MENU + 4 * i, w) for i, w in enumerate(menu)]
    out += ['0x%08X=0x%08X' % h for h in hooks]
    print(' '.join(out))
    sys.stderr.write('trait badge: %d words; Hero menu: %d words\n' % (len(words), len(menu)))
    if DEBUG:
        base = a.labels['counters']
        sys.stderr.write('debug counters at 0x%08X:\n' % base)
        for i, n in enumerate(COUNTERS):
            sys.stderr.write('  0x%08X  %s\n' % (base + 4 * i, n))


if __name__ == '__main__':
    main()
