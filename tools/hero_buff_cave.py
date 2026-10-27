#!/usr/bin/env python3
"""Hero's buffs and Oomph's downside, native part: prints rpx_patch.py args (ADDR=VALUE words).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/strike_cave.py) $(python3 tools/hero_buff_cave.py)

(always with strike_cave.py: its hitbox and throw paths end by branching here, and this goes back.)

Hero's MSC (fighters/brave/brave.c brave_buff_update) keeps bits in the trait marker (WorkModule int
0x1000008E = 0x4B49xxxx, as Kirby's, tools/strike_cave.py):
- OOMPH_BIT (0x20), Oomph on his physical attacks (not while in a special): hitbox damage x1.6 and
  knockback x1.1 (Ultimate's special_lw attack_up: attack x1.6, reaction x1.1); throws x1.6 damage;
- PSYCHE_BIT (0x40), Psyche Up's next physical hit: knockback x1.2 and shield damage x1.65;
- TAKEN_BIT (0x80), Oomph's downside: the damage he takes x1.2.

1. Hitboxes (HB_ATK, after strike_cave.py's set_attack hook; r26 = the hitbox's slot, r28 its
   AttackModule): knockback as base, growth and set knockback (+0x2C, +0x24, +0x28, ints) x the percent
   (110 / 120 / 132), rounded; Oomph's damage (+0x18); Psyche Up's shield damage: the slot's added shield
   damage (+0x58, a signed half) made so damage + it is x1.65 (the Hitbox command's ShieldDamage,
   parameter 18). Offsets: the ACMD Hitbox handler 0x02BDB0EC (docs/native-notes.md).
2. Throws (HB_THROW, after strike_cave.py's throw hook): the throw's damage (0x78(r1)) x1.6.
3. Damage taken (HOOK_VIC, the victim hit handler 0x02C25318's first word: r4 = the victim's module
   accessor, r5 = the hit info): the hit info's damage (+0xC) x1.2 when the victim has TAKEN_BIT. Its
   knockback (+0x10) is already worked out by then: only the percent grows.

Hero's critical hits need nothing here: his smash scripts keep both of Ultimate's hitbox sets
(tools/brave_build.py CRIT_INT).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402
import strike_cave as S  # noqa: E402

CAVE = S.HERO_CAVE              # free grown .text: copy_custom_cave.py's spawners end before 0x04B9E800
LIMIT = 0x04BA0000              # kind_expand.py from here
HOOK_VIC = 0x02C25318           # the victim hit handler's first word: stwu r1, -0x110(r1)
HOOK_VIC_WORD = 0x9421FEF0
ATK_BACK = S.HOOK_ATK + 4
THROW_BACK = S.HOOK_THROW + 4
OOMPH_BIT = 0x20
PSYCHE_BIT = 0x40
TAKEN_BIT = 0x80
OOMPH_DAMAGE = 1.6
OOMPH_KB = 110                  # percent
PSYCHE_KB = 120
PSYCHE_SHIELD = 165
TAKEN = 1.2

SOURCE = """
        b hb_atk                        # HB_ATK (strike_cave.py's atk_done)
        b hb_throw                      # HB_THROW (its throw_done)
        b hb_vic                        # HOOK_VIC

hb_atk:                                 # r26 = the hitbox's slot, r28 = its AttackModule
%(o_atk)s
%(m_atk)s
        li r10, 100                     # knockback, percent
        li r8, 100
        andi. r0, r11, %(OOMPH)d
        beq atk_ps
        mulli r10, r10, %(OKB)d
        divwu r10, r10, r8
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f0, 0x18(r26)               # damage x1.6
        lfs f13, 0(r12)
        fmuls f0, f0, f13
        stfs f0, 0x18(r26)
atk_ps:
        andi. r0, r11, %(PSYCHE)d
        beq atk_kb
        mulli r10, r10, %(PKB)d
        divwu r10, r10, r8
atk_kb:
%(KB)s
        andi. r0, r11, %(PSYCHE)d
        beq atk_out
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f0, 0x18(r26)               # d = (int) damage
        fctiwz f0, f0
        stfd f0, 8(r12)
        lwz r10, 0xC(r12)
        lha r12, 0x58(r26)              # its added shield damage b (not in r0: addi r0 reads 0)
        add r12, r12, r10
        mulli r12, r12, %(PSH)d         # b = (d + b) x 1.65 - d, rounded
        addi r12, r12, 50
        divw r12, r12, r8
        subf r12, r10, r12
        sth r12, 0x58(r26)
atk_out:
        lwz r8, 0(r28)                  # set_attack's own instruction
        b %(ATK_BACK)s

hb_throw:                               # r30 = AttackModule, the throw's attack data at 0x78(r1)
%(o_throw)s
%(m_throw)s
        lis r12, consts@ha
        lfs f13, consts@l(r12)
        lfs f0, 0x78(r1)                # damage x1.6
        fmuls f0, f0, f13
        stfs f0, 0x78(r1)
throw_out:
        lwz r12, 0(r30)                 # the handler's own instruction
        b %(THROW_BACK)s

hb_vic:                                 # r4 = the victim's module accessor, r5 = the hit info
%(c4)s
%(c5)s
        lwz r12, 0x28(r4)               # its WorkModule
%(m_vic)s
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f0, 0xC(r5)                 # the damage x1.2
        lfs f13, 4(r12)
        fmuls f0, f0, f13
        stfs f0, 0xC(r5)
vic_out:
        stwu r1, -0x110(r1)             # the handler's own instruction
        b %(VIC_BACK)s

consts:
        .float %(OD)r
        .float %(TK)r
        .word 0                         # 8: a double's room (fctiwz)
        .word 0
"""


def kb_lines():
    """knockback ints (+0x2C base, +0x24 growth, +0x28 set) x r10 / 100 (r8), rounded (in r12: `addi r0`
    reads 0, not r0)"""
    out = []
    for off in (0x2C, 0x24, 0x28):
        out += ["        lwz r12, 0x%X(r26)" % off, "        mullw r12, r12, r10", "        addi r12, r12, 50",
                "        divwu r12, r12, r8", "        stw r12, 0x%X(r26)" % off]
    return "\n".join(out)


def assemble():
    a = Asm(CAVE)
    a.asm(SOURCE % dict(
        o_atk=S.owner_wm("r28", "atk_out"), m_atk=S.marker("r12", "atk_out", bit=OOMPH_BIT | PSYCHE_BIT),
        o_throw=S.owner_wm("r30", "throw_out"), m_throw=S.marker("r12", "throw_out", bit=OOMPH_BIT),
        c4=S.chk("r4", "vic_out"), c5=S.chk("r5", "vic_out"), m_vic=S.marker("r12", "vic_out", bit=TAKEN_BIT),
        OOMPH=OOMPH_BIT, PSYCHE=PSYCHE_BIT, OKB=OOMPH_KB, PKB=PSYCHE_KB, PSH=PSYCHE_SHIELD, KB=kb_lines(),
        ATK_BACK="0x%08X" % ATK_BACK, THROW_BACK="0x%08X" % THROW_BACK, VIC_BACK="0x%08X" % (HOOK_VIC + 4),
        OD=OOMPH_DAMAGE, TK=TAKEN))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, "hero buff cave too big: %d words" % len(words)
    assert a.labels.get("hb_atk") and CAVE == S.HB_ATK and CAVE + 4 == S.HB_THROW
    return a, words


def main():
    a, words = assemble()
    out = ["0x%08X=0x%08X" % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append("0x%08X=0x%08X" % (HOOK_VIC, S.branch(HOOK_VIC, CAVE + 8)))
    print(" ".join(out))


if __name__ == "__main__":
    main()
