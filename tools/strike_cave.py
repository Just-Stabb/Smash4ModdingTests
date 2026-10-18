#!/usr/bin/env python3
"""Kirby's Strike trait, native part: prints rpx_patch.py args (ADDR=VALUE words).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/position_vars_cave.py) \\
      $(python3 tools/strike_cave.py)

(after position_vars_cave.py, whose grow:0x04B79000 makes the code space this uses.)

A fighter is "Strike Kirby" when its WorkModule instance int 0x1000008E (Kirby's trait marker,
written every frame by kirby_trait_update() in fighters/kirby/kirby.c) is 0x4B49xxxx with bit
STRIKE_BIT (0x8) set. (Bits 0-2 are the stat profile, tools/kirby_stat_cave.py.) Then:

1. Hitboxes (HOOK_ATK, in AttackModuleImpl::set_attack 0x02C086A8 right after the attack data is
   copied into its slot): damage (+0x18) x DAMAGE_MULT (1.15) and the hitbox's hitlag multiplier
   (+0x34) x HITSTOP_MULT (1.2), for hitboxes owned by Strike Kirby. AttackModule +4 is the owning
   battle object; only fighters (object ID >> 28 == 0) are looked at, so projectiles and other
   articles (weapons, their own objects) are never changed. Every hitbox command (ACMD Hitbox,
   Special_Hitbox, ..., MSC) goes through set_attack.
2. Hitstop (HOOK_HS, the generic hitstop calculation 0x02C27638, called for both sides of a hit:
   r4 = accessor of the fighter being stopped, r5 = hit info, r6 = 1 for the attacker, 0 for the
   victim): when Strike Kirby is the attacker, his own hitstop is computed with damage / 1.15 and
   multiplier / 1.2, i.e. exactly as without Strike. The victim's isn't touched, so it gets the
   hitbox's x1.2 multiplier (on top of the extra damage's own share of hitstop).

Hitstop = floor(min((damage x 0.3846154 + 5) x multiplier, 30)) (0x02C26724, called from
0x02C2678C with the hitbox data's multiplier +0x34 and effect +0x43); see docs/native-notes.md.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B78E00           # grown .text (position_vars_cave.py GROW_END); its own blocks end before
LIMIT = 0x04B79000
HOOK_ATK = 0x02C08730       # set_attack, after the copy loop: lwz r8, 0(r28)
HOOK_HS = 0x02C27638        # hitstop calc: mr r11, r5
CALC_HITLAG = 0x02C2678C
INT_INDEX = 0x8E
MAGIC = 0x4B49
STRIKE_BIT = 0x8
DAMAGE_MULT = 1.15
HITSTOP_MULT = 1.2
BIAS = 1.00001              # so damage / 1.15 x 1.15 and x1.2 / 1.2 don't land just below a whole frame


def chk(reg, fail):
    """bne fail unless reg is a word-aligned pointer in 0x10000000-0x4FFFFFFF (data / heap)."""
    return """
        addis r0, %s, -0x1000
        rlwinm. r0, r0, 0, 0, 1
        bne %s
        andi. r0, %s, 3
        bne %s""" % (reg, fail, reg, fail)


def marker(wm, fail):
    """r11 = the trait marker of WorkModule wm (int 0x1000008E), else bne fail. Uses r0, r10, r11."""
    return chk(wm, fail) + """
        lwz r10, 8(%(wm)s)              # category table
%(c10)s
        lwz r11, 4(r10)                 # category 1 (instance ints)
%(c11)s
        lwz r10, 8(r11)                 # int count (top 2 bits are flags)
        rlwinm r10, r10, 0, 2, 31
        cmplwi r10, %(n)d
        blt %(fail)s
        lwz r11, 0xC(r11)               # ints
%(c11)s
        lwz r11, %(off)d(r11)
        srwi r10, r11, 16
        cmplwi r10, %(magic)d
        bne %(fail)s
        andi. r0, r11, %(bit)d
        beq %(fail)s""" % dict(wm=wm, fail=fail, c10=chk("r10", fail), c11=chk("r11", fail),
                               n=INT_INDEX + 1, off=INT_INDEX * 4, magic=MAGIC, bit=STRIKE_BIT)


SOURCE = """
strike_atk:                             # r26 = the new hitbox's slot, r28 = AttackModule
        lwz r12, 4(r28)                 # owner battle object
%(c12_atk)s
        lwz r11, 0(r12)                 # object ID: fighters have category 0
        srwi. r0, r11, 28
        bne atk_done
        lwz r12, 0xC(r12)               # module accessor
%(c12_atk)s
        lwz r12, 0x28(r12)              # WorkModule
%(m12_atk)s
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f0, 0x18(r26)               # damage x 1.15
        lfs f13, 0(r12)
        fmuls f0, f0, f13
        stfs f0, 0x18(r26)
        lfs f0, 0x34(r26)               # hitlag multiplier x 1.2
        lfs f13, 4(r12)
        fmuls f0, f0, f13
        stfs f0, 0x34(r26)
atk_done:
        lwz r8, 0(r28)                  # set_attack's own instruction
        b %(ATK_BACK)s

strike_hs:                              # r4 accessor, r5 hit info, r6 1 = attacker side, f1 mult
        cmpwi r6, 1
        bne hs_orig
%(c4_hs)s
        lwz r12, 0x28(r4)               # WorkModule
%(m12_hs)s
        lfs f3, 0x10(r5)                # the original's "no hitstop" check
        lis r12, 0x1010
        lfs f0, 0x5D98(r12)
        li r3, 0
        fcmpu cr0, f3, f0
        blelr
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f0, 0xC(r12)
        fmuls f2, f1, f0                # multiplier / 1.2 (the hitbox's was x1.2)
        lfs f0, 8(r12)
        lfs f1, 0xC(r5)
        fmuls f1, f1, f0                # damage / 1.15
        mr r3, r4
        addi r4, r5, 0x44               # hitbox data
        mr r5, r6
        li r6, 1
        b %(CALC)s
hs_orig:
        mr r11, r5                      # the hitstop calc's own instruction
        b %(HS_BACK)s

consts:
        .float %(DM)r
        .float %(HM)r
        .float %(IDM)r
        .float %(IHM)r
"""


def assemble():
    a = Asm(CAVE)
    a.asm(SOURCE % dict(
        c12_atk=chk("r12", "atk_done"), m12_atk=marker("r12", "atk_done"),
        c4_hs=chk("r4", "hs_orig"), m12_hs=marker("r12", "hs_orig"),
        ATK_BACK="0x%08X" % (HOOK_ATK + 4), HS_BACK="0x%08X" % (HOOK_HS + 4), CALC="0x%08X" % CALC_HITLAG,
        DM=DAMAGE_MULT, HM=HITSTOP_MULT, IDM=BIAS / DAMAGE_MULT, IHM=1.0 / HITSTOP_MULT))
    words = a.words()
    assert CAVE + 4 * len(words) <= LIMIT, "strike cave too big: %d words" % len(words)
    return a, words


def branch(src, dst):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000
    return (18 << 26) | (off & 0x3FFFFFC)


def main():
    a, words = assemble()
    out = ["0x%08X=0x%08X" % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out.append("0x%08X=0x%08X" % (HOOK_ATK, branch(HOOK_ATK, a.labels["strike_atk"])))
    out.append("0x%08X=0x%08X" % (HOOK_HS, branch(HOOK_HS, a.labels["strike_hs"])))
    print(" ".join(out))


if __name__ == "__main__":
    main()
