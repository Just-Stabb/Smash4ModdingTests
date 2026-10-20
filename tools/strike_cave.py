#!/usr/bin/env python3
"""Kirby's Strike trait, native part: prints rpx_patch.py args (ADDR=VALUE words).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/position_vars_cave.py) \\
      $(python3 tools/strike_cave.py)

(after position_vars_cave.py, whose grow:0x04B7C000 makes the code space this uses.)

A fighter is "Strike Kirby" when its WorkModule instance int 0x1000008E (Kirby's trait marker,
written every frame by kirby_trait_update() in fighters/kirby/kirby.c) is 0x4B49xxxx with bit
STRIKE_BIT (0x8) set. (Bits 0-2 are the stat profile, tools/kirby_stat_cave.py.) CRIT_BIT (0x10) is
set by the MSC for the whole of a smash attack that rolled a critical hit. Then:

1. Hitboxes (HOOK_ATK, in AttackModuleImpl::set_attack 0x02C086A8 right after the attack data is
   copied into its slot): damage (+0x18) x DAMAGE_MULT (1.15) and the hitbox's hitlag multiplier
   (+0x34) x HITSTOP_MULT (1.2), for hitboxes owned by Strike Kirby. AttackModule +4 is the owner's
   module accessor, whose WorkModule (+0x28) holds the marker; projectiles and other articles have
   their own accessor and WorkModule (no marker), so they're never changed. Every hitbox command (ACMD Hitbox,
   Special_Hitbox, ..., MSC) goes through set_attack. Critical hit: damage x CRIT_MULT (2) more,
   and the multiplier x2 x (s k + 5) / (2s k + 5) (s = the Strike damage, k = 0.3846154) so that
   the opponent's hitstop is exactly 2x the Strike hit's.
2. Hitstop (HOOK_HS, the generic hitstop calculation 0x02C27638, called for both sides of a hit:
   r4 = accessor of the fighter being stopped, r5 = hit info, r6 = 1 for the attacker, 0 for the
   victim): when Strike Kirby is the attacker, his own hitstop is computed with damage / 1.15 and
   multiplier / 1.2, i.e. exactly as without Strike (critical hit: damage / 2.3 and the crit's
   ratio undone, so his hitstop is 2x his Strike one, which is the normal one). The victim's isn't
   touched, so it gets the hitbox's x1.2 multiplier (on top of the extra damage's own share of
   hitstop); on a crit, 2x that.
3. Throws (HOOK_THROW, in AttackModule's MSC handler 0x02C0ACFC, case 0x2716 / 0x2717, which every
   throw command (ACMD Throw_Specifier, Throw_Specifier2, Intensity_Throw_Specifier) goes
   through, just before it hands the throw's attack data (at 0x78(r1), damage first) to vtable
   +0x64): damage x DAMAGE_MULT for Strike Kirby.

Hitstop = floor(min((damage x 0.3846154 + 5) x multiplier, 30)) (0x02C26724, called from
0x02C2678C with the hitbox data's multiplier +0x34 and effect +0x43); see docs/native-notes.md.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B78A00           # grown .text (position_vars_cave.py GROW_END); its own blocks end before
LIMIT = 0x04B78E80           # copy_fx_cave.py from here
HOOK_ATK = 0x02C08730       # set_attack, after the copy loop: lwz r8, 0(r28)
HOOK_HS = 0x02C27638        # hitstop calc: mr r11, r5
HOOK_THROW = 0x02C0B77C     # AttackModule MSC handler, throw (0x2716) case, before vt+0x64: lwz r12, 0(r30)
CALC_HITLAG = 0x02C2678C
INT_INDEX = 0x8E
MAGIC = 0x4B49
STRIKE_BIT = 0x8
CRIT_BIT = 0x10
DAMAGE_MULT = 1.15
HITSTOP_MULT = 1.2
CRIT_MULT = 2.0
BIAS = 1.00001              # so damage / 1.15 x 1.15 and x1.2 / 1.2 don't land just below a whole frame


def chk(reg, fail):
    """bne fail unless reg is a word-aligned pointer in 0x10000000-0x8FFFFFFF (data / heap; was
    0x10000000-0x4FFFFFFF, widened in case the game's objects sit higher in Cemu)."""
    return """
        addis r0, %s, -0x1000
        rlwinm. r0, r0, 0, 0, 0
        bne %s
        andi. r0, %s, 3
        bne %s""" % (reg, fail, reg, fail)


def marker(wm, fail, save=False):
    """r11 = the trait marker of WorkModule wm (int 0x1000008E) with the Strike bit, else branch to
    fail. Uses r0, r10, r11 (and r12 with save: debug words DBG_MARKER / DBG_KI / DBG_KI_COUNT)."""
    return chk(wm, fail) + """
        lwz r10, 8(%(wm)s)              # category table
%(c10)s
        lwz r11, 0(r10)                 # category 0 (ID 0x1000008E: (id >> 24) & 0xF = 0, get_int
                                        # 0x0200F7F0); the first versions read category 1 (+4)
%(c11)s
        lwz r10, 8(r11)                 # int count (top 2 bits are flags)
        rlwinm r10, r10, 0, 2, 31
        cmplwi r10, %(n)d
        blt %(fail)s
        lwz r11, 0xC(r11)               # ints
%(c11)s
        lwz r11, %(off)d(r11)
%(save)s
        srwi r10, r11, 16
        cmplwi r10, %(magic)d
        bne %(fail)s
%(save_ki)s
        andi. r0, r11, %(bit)d
        beq %(fail)s""" % dict(wm=wm, fail=fail, c10=chk("r10", fail), c11=chk("r11", fail),
                               n=INT_INDEX + 1, off=INT_INDEX * 4, magic=MAGIC, bit=STRIKE_BIT,
                               save=dbg_store("r11", DBG_MARKER) if save else "",
                               save_ki=(dbg_store("r11", DBG_KI) + "\n" + inc(DBG_KI_COUNT)) if save else "")


# Debug words after the four counters (counters + 4 * index), for Cemu's memory viewer. Every
# fighter's hitboxes overwrite the "last" ones, so read them in training with only Kirby attacking.
DBG_OWNER_OK = 4      # count: hitboxes whose owner lookup worked
DBG_AM = 5            # last AttackModule seen
DBG_ACC = 6           # its [+4] (the accessor)
DBG_ACC_AM = 7        # [accessor + 0x50] (should equal DBG_AM)
DBG_WM = 8            # [accessor + 0x28] (the WorkModule)
DBG_MARKER = 9        # its int 0x1000008E
DBG_KI = 10           # last marker with Kirby's 0x4B49 magic (Strike bit = 0x8)
DBG_KI_COUNT = 11     # count: hitboxes from a fighter with the 0x4B49 magic
DBG_WORDS = 12


def dbg_store(reg, k):
    """counters[k] = reg (uses r12)"""
    return """        lis r12, counters@ha
        addi r12, r12, counters@l
        stw %s, %d(r12)""" % (reg, 4 * k)


def inc(k):
    """counters[k] += 1 (uses r10, r12; not r0: `addi r0, r0, 1` is `li r0, 1`, which kept the
    first version's counters at 1)"""
    return """        lis r12, counters@ha
        addi r12, r12, counters@l
        lwz r10, %d(r12)
        addi r10, r10, 1
        stw r10, %d(r12)""" % (4 * k, 4 * k)


def owner_wm(am, fail, save=False):
    """r12 = the WorkModule of the object whose AttackModule is am, else branch to fail. AttackModule +4
    is its module accessor (AttackModuleImpl's constructor 0x02C077F4 stores its argument there; the
    fighter set-up 0x02E53764 passes the accessor, then stores the module at accessor +0x50), and the
    accessor has the WorkModule at +0x28. Checks accessor +0x50 == am. Uses r0, r12 (and r10, r11
    with save: debug words DBG_AM..DBG_WM, DBG_OWNER_OK)."""
    if not save:
        return chk(am, fail) + """
        lwz r12, 4(%(am)s)              # module accessor
%(c12)s
        lwz r0, 0x50(r12)               # its AttackModule
        cmplw r0, %(am)s
        bne %(fail)s
        lwz r12, 0x28(r12)              # WorkModule""" % dict(am=am, fail=fail, c12=chk("r12", fail))
    return """
        lis r10, counters@ha
        addi r10, r10, counters@l
        stw %(am)s, %(o_am)d(r10)
        li r0, 0
        stw r0, %(o_acc)d(r10)
        stw r0, %(o_acc_am)d(r10)
        stw r0, %(o_wm)d(r10)
        stw r0, %(o_mk)d(r10)""" % dict(am=am, o_am=4 * DBG_AM, o_acc=4 * DBG_ACC, o_acc_am=4 * DBG_ACC_AM,
                                       o_wm=4 * DBG_WM, o_mk=4 * DBG_MARKER) + chk(am, fail) + """
        lwz r12, 4(%(am)s)              # module accessor
        stw r12, %(o_acc)d(r10)
%(c12)s
        lwz r0, 0x50(r12)               # its AttackModule
        stw r0, %(o_acc_am)d(r10)
        cmplw r0, %(am)s
        bne %(fail)s
        lwz r12, 0x28(r12)              # WorkModule
        stw r12, %(o_wm)d(r10)
        lwz r11, %(o_ok)d(r10)
        addi r11, r11, 1
        stw r11, %(o_ok)d(r10)""" % dict(am=am, fail=fail, c12=chk("r12", fail), o_acc=4 * DBG_ACC,
                                         o_acc_am=4 * DBG_ACC_AM, o_wm=4 * DBG_WM, o_ok=4 * DBG_OWNER_OK)


# Earlier versions looked for the owner through [AM+4] +0xC (taking +4 for the battle object) and
# then by scanning the fighter table; neither found Kirby in game. +4 is the accessor itself.


SOURCE = """
strike_atk:                             # r26 = the new hitbox's slot, r28 = AttackModule
%(INC0)s
%(o_atk)s
%(m12_atk)s
        lis r12, consts@ha
        addi r12, r12, consts@l
        lfs f0, 0x18(r26)               # damage x 1.15
        lfs f13, 0(r12)
        fmuls f0, f0, f13
        lfs f12, 0x34(r26)              # hitlag multiplier x 1.2
        lfs f13, 4(r12)
        fmuls f12, f12, f13
        andi. r0, r11, %(CRIT)d
        beq atk_store
        lfs f13, 0x18(r12)              # critical hit (s = Strike damage): damage x2, and the
        lfs f11, 0x1C(r12)              # multiplier x2 x (s k + 5) / (2s k + 5), so the opponent's
        fmadds f10, f0, f13, f11        # hitstop (2s k + 5) x multiplier is 2x the Strike one
        fadds f9, f0, f0
        fmadds f9, f9, f13, f11
        fdivs f10, f10, f9
        fmuls f12, f12, f10
        lfs f13, 0x10(r12)
        fmuls f0, f0, f13
        fmuls f12, f12, f13
atk_store:
        stfs f0, 0x18(r26)
        stfs f12, 0x34(r26)
%(INC1)s
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
        lfs f9, 0xC(r5)                 # the hit's damage D
        lfs f0, 8(r12)
        andi. r0, r11, %(CRIT)d
        beq hs_damage
        lfs f13, 0x18(r12)              # critical hit: multiplier also x (D k + 5) / (D/2 k + 5)
        lfs f11, 0x1C(r12)              # (undoes the crit's ratio, keeps its x2) and damage / 2.3:
        lfs f8, 0x20(r12)               # Kirby's hitstop = 2x the normal one
        fmadds f10, f9, f13, f11
        fmuls f7, f9, f8
        fmadds f7, f7, f13, f11
        fdivs f10, f10, f7
        fmuls f2, f2, f10
        lfs f8, 0x24(r12)
        fmuls f2, f2, f8
        lfs f0, 0x14(r12)
hs_damage:
        fmuls f1, f9, f0                # damage / 1.15
%(INC2)s
        mr r3, r4
        addi r4, r5, 0x44               # hitbox data
        mr r5, r6
        li r6, 1
        b %(CALC)s
hs_orig:
        mr r11, r5                      # the hitstop calc's own instruction
        b %(HS_BACK)s

strike_throw:                           # r30 = AttackModule, throw attack data at 0x78(r1)
%(o_throw)s
%(m12_throw)s
        lis r12, consts@ha
        lfs f13, consts@l(r12)
        lfs f0, 0x78(r1)                # damage x 1.15
        fmuls f0, f0, f13
        stfs f0, 0x78(r1)
%(INC3)s
throw_done:
        lwz r12, 0(r30)                 # the handler's own instruction
        b %(THROW_BACK)s

counters:                               # debug counts (see docs/native-notes.md): hitboxes seen, hitboxes
        .word 0                         # scaled, own-hitstop adjustments, throws scaled, then the
        .word 0                         # DBG_* words
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
consts:
        .float %(DM)r
        .float %(HM)r
        .float %(IDM)r
        .float %(IHM)r
        .float %(CM)r
        .float %(ICM)r
        .float 0.3846154                # hitstop per damage (common params +0x90)
        .float 5.0                      # hitstop base (+0x94)
        .float 0.5
        .float %(BIAS)r
"""


def assemble():
    a = Asm(CAVE)
    a.asm(SOURCE % dict(
        INC0=inc(0), INC1=inc(1), INC2=inc(2), INC3=inc(3),
        o_atk=owner_wm("r28", "atk_done", save=True), m12_atk=marker("r12", "atk_done", save=True),
        o_throw=owner_wm("r30", "throw_done"), m12_throw=marker("r12", "throw_done"), CRIT=CRIT_BIT,
        THROW_BACK="0x%08X" % (HOOK_THROW + 4), CM=CRIT_MULT, ICM=BIAS / (DAMAGE_MULT * CRIT_MULT), BIAS=BIAS,
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
    out.append("0x%08X=0x%08X" % (HOOK_THROW, branch(HOOK_THROW, a.labels["strike_throw"])))
    print(" ".join(out))


if __name__ == "__main__":
    main()
