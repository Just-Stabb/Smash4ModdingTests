#!/usr/bin/env python3
"""Smash Run step 1: enemies on the Smash Run stages (docs/smash-run-port.md, "Step 1: enemies on the field").
Prints rpx_patch.py args (after the standard build's and tools/smashrun_menu.py's), or patches an RPX:

  python3 tools/smashrun_field_cave.py [--minions]                 the args
  python3 tools/smashrun_field_cave.py [--minions] IN.rpx OUT.rpx  IN with them (checks the hook words first)

On a battle whose stage kind (`*(0x1047277C)`) is one of the Smash Run slots (0x82-0x95, stage_slot_cave.py)
the game's own enemy system runs as in Classic's Master Fortress. The enemies (ENEMY_SETS):
- "smashrun" (the default, step 2a): Smash Run's own Plasma Wisp 0x12, Darios 0x1D, Stalfos 0x30 and Zima 0x0E (the
  converted 3DS enemies), driven by their Master Fortress twins' behaviours through tools/smashrun_enemy_cave.py
  (which must be applied too); the resource request also loads mczakoplasmawisp 0x57 (its weapons / effects).
- "minions" (`--minions`, step 1): the four Fortress minions themselves, mczakoplasmawisp 0x57, mczakodarios 0x58,
  mczakostalfos 0x59, mczakozima 0x5A.

- A: the EnemyManager is made for a battle only when 0x02D9E1F4 says so (Classic boss rounds, the Crazy Hand event,
  stage kinds 0x1C / 8 / 0x13 / 3). Its last test, 0x02D9E2DC `cmpwi r0,3` (r0 = the stage kind), -> a cave that
  also answers yes for 0x82-0x95.
- B: the manager's category (0x02D99FD4 stores it at mgr+0x5EC; 0 fs, 1 ml, 2 sm): 0x02D99FF8 `stw r31,0x5EC(r3)`
  -> a cave that makes it 2 (sm) on the Smash Run stages before the store. r31 is what the function then uses
  to open param/enemy/sm, so the sm accessor (0x026B40B8, kinds 0x50-0x5A) loads
  param/enemy/sm/enemy_param_vl_mczako*.bin into the param manager's per-kind slots. (The ml accessor has no case
  for the minions: their slots would stay null and the enemy's activation reads them unchecked.)
- C: battle load 0x02D9A454's sm path, 0x02D9A568 `bl 0x02DC66D0` (the accessor set-up) -> a cave that makes the
  same call, then requests the set's kinds' resources (0x02DAE314(mgr+0x28, kind): model, motion, animcmd, sound,
  effect, and the weapons in the kind's article table 0x10352794) on the Smash Run stages.
- D: every frame the manager updates (0x02D9B554, sm path), 0x02D9B6F8 `bl 0x02D9B1A8` -> the spawner, which ends
  in that call: on a Smash Run stage, every INTERVAL frames, while fewer than MAX_ALIVE of the set's four kinds live
  (mgr+0x52A + 2 * kind: the manager's per-kind live counts), it spawns the set's next kind (in turn) beside the player
  (fighter manager *(0x102F7024) entry 0: 0x02E46DEC(entry, &handle, entry+0x14E9) and 0x02BEF6E0(&xyz,
  &handle), as the leftover field generator 0x02D98A0C does), DX to the left / right in turn, facing the player,
  through 0x02D9BCFC(mgr, &EnemyCreateParam) (owner none: hostile to every fighter, as on Pyrosphere and in the
  Fortress). Placement +0x20 (the set's table): 1 (ray-cast down to the ground) for Stalfos / Zima, 2 (as given)
  for the floaters.

Space: 0x04B7D100-0x04B7E000 (stage_slot_cave.py's space after its code; smashrun_menu.py has 0x04B7D000-0x04B7D100).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B7D100
DATA = 0x04B7DF00               # +0 frame counter, +4 next kind, +8 side, floats from +0x10
LIMIT = 0x04B7E000
STAGE_KIND = 0x1047277C
SR_FIRST, SR_COUNT = 0x82, 0x14
# (kind, placement) in spawn order (4: the turn counter wraps with andi 3), and the kinds whose resources load
ENEMY_SETS = {
    'smashrun': (((0x12, 2), (0x1D, 2), (0x30, 1), (0x0E, 1)), (0x12, 0x1D, 0x30, 0x0E, 0x57)),
    'minions': (((0x57, 2), (0x58, 2), (0x59, 1), (0x5A, 1)), (0x57, 0x58, 0x59, 0x5A)),
}
ENEMIES = 'smashrun'
SPAWNS, REQUESTS = ENEMY_SETS[ENEMIES]
KINDS = tuple(k for k, _m in SPAWNS)
INTERVAL = 150                  # frames between spawns (2.5 s)
MAX_ALIVE = 6
DX, DY = 70.0, 30.0             # spawn offset from the player

SITE_A, WORD_A = 0x02D9E2DC, 0x2C000003      # cmpwi r0, 3
SITE_B, WORD_B = 0x02D99FF8, 0x93E305EC      # stw r31, 0x5EC(r3)
SITE_C, WORD_C = 0x02D9A568, 0x4802C169      # bl 0x02DC66D0
SITE_D, WORD_D = 0x02D9B6F8, 0x4BFFFAB1      # bl 0x02D9B1A8

ACCESSOR_SETUP = 0x02DC66D0
REQUEST = 0x02DAE314
UPDATE_REST = 0x02D9B1A8
FIGHTER_MGR = 0x102F7024
POS_HANDLE = 0x02E46DEC
HANDLE_NULL = 0x02BEF50C
HANDLE_POS = 0x02BEF6E0
SPAWN = 0x02D9BCFC


def sr_check(a, reg='r12', far=None):
    """cr0 'le' (unsigned) when *(STAGE_KIND) is a Smash Run stage"""
    a.asm("""
        lis {r}, 0x{hi:04X}
        lwz {r}, {lo}({r})
        addi {r}, {r}, -0x{first:X}
        cmplwi {r}, 0x{last:X}
    """.format(r=reg, hi=(STAGE_KIND + 0x8000) >> 16, lo=struct.unpack('>h', struct.pack('>H', STAGE_KIND & 0xFFFF))[0],
               first=SR_FIRST, last=SR_COUNT - 1))


def assemble():
    a = Asm(CAVE)
    # A: the manager for Smash Run stages (r0 = stage kind)
    a.asm("""
    cave_a:
        cmpwi r0, 3
        beq.far yes_a
        mr r12, r0                  # (addi rD, r0, x reads 0, not r0)
        addi r12, r12, -0x%X
        cmplwi r12, 0x%X
        ble.far yes_a
        b 0x02D9E2FC
    yes_a:
        b 0x02D9E2E4
    """ % (SR_FIRST, SR_COUNT - 1))
    # B: category sm on Smash Run stages (r3 = mgr, r31 = category)
    a.asm("cave_b:")
    sr_check(a)
    a.asm("""
        bgt b_store
        li r31, 2
    b_store:
        stw r31, 0x5EC(r3)
        b 0x%08X
    """ % (SITE_B + 4))
    # C: the accessor set-up, then the four kinds' resources (r31 = mgr)
    a.asm("""
    cave_c:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stw r30, 0x18(r1)
        bl 0x%08X
    """ % ACCESSOR_SETUP)
    sr_check(a)
    a.asm("bgt c_done")
    for k in REQUESTS:
        a.asm("""
        addi r3, r31, 0x28
        li r4, 0x%X
        bl 0x%08X
        """ % (k, REQUEST))
    a.asm("""
    c_done:
        lwz r30, 0x18(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    """)
    # D: the spawner (r3 = mgr), ends in the manager's own next step
    a.asm("""
    cave_d:
        mflr r0
        stwu r1, -0x80(r1)
        stw r0, 0x84(r1)
        stw r31, 0x7C(r1)
        stw r30, 0x78(r1)
        mr r31, r3
    """)
    sr_check(a)
    a.asm("""
        bgt d_out
        lis r30, 0x%04X
        addi r30, r30, %d
        lwz r12, 0(r30)
        addi r12, r12, 1
        stw r12, 0(r30)
        cmpwi r12, %d
        blt d_out
        li r12, 0
        stw r12, 0(r30)
    """ % ((DATA + 0x8000) >> 16, DATA & 0xFFFF if DATA & 0xFFFF < 0x8000 else (DATA & 0xFFFF) - 0x10000,
           INTERVAL))
    a.asm("li r12, 0")
    for k in KINDS:
        a.asm("""
        lhz r11, 0x%X(r31)
        add r12, r12, r11
        """ % (0x52A + 2 * k))
    a.asm("""
        cmpwi r12, %d
        bge d_out
        lis r12, 0x%04X
        lwz r12, 0x%04X(r12)
        cmpwi r12, 0
        beq d_out
        lwz r3, 0x24(r12)
        cmpwi r3, 0
        beq d_out
        lbz r5, 0x14E9(r3)
        addi r4, r1, 0x60
        bl 0x%08X
        addi r3, r1, 0x60
        bl 0x%08X
        cmpwi r3, 0
        bne d_out
        addi r3, r1, 0x68
        addi r4, r1, 0x60
        bl 0x%08X
        li r0, 0
    """ % (MAX_ALIVE, (FIGHTER_MGR + 0x8000) >> 16, FIGHTER_MGR & 0xFFFF, POS_HANDLE, HANDLE_NULL, HANDLE_POS))
    for off in range(0, 0x3C, 4):
        a.asm("stw r0, 0x%X(r1)" % (0x20 + off))
    a.asm("""
        lwz r12, 4(r30)
        addi r11, r12, 1
        andi. r11, r11, 3
        stw r11, 4(r30)
        lis r11, spawn_table@ha
        addi r11, r11, spawn_table@l
        slwi r12, r12, 3
        add r11, r11, r12
        lwz r12, 0(r11)
        stw r12, 0x20(r1)
        lwz r11, 4(r11)
        stw r11, 0x40(r1)
        lfs f1, 0x10(r30)
        stfs f1, 0x28(r1)
        lwz r12, 8(r30)
        xori r12, r12, 1
        stw r12, 8(r30)
        lfs f2, 0x18(r30)
        cmpwi r12, 0
        bne d_side
        fneg f2, f2
    d_side:
        lfs f3, 0x68(r1)
        fadds f4, f3, f2
        stfs f4, 0x2C(r1)
        lfs f5, 0x6C(r1)
        lfs f6, 0x1C(r30)
        fadds f5, f5, f6
        stfs f5, 0x30(r1)
        lfs f7, 0x70(r1)
        stfs f7, 0x34(r1)
        lfs f8, 0x14(r30)
        cmpwi r12, 0
        bne d_face
        lfs f8, 0x10(r30)
    d_face:
        stfs f8, 0x38(r1)
        mr r3, r31
        addi r4, r1, 0x20
        bl 0x%08X
    d_out:
        mr r3, r31
        lwz r30, 0x78(r1)
        lwz r31, 0x7C(r1)
        lwz r0, 0x84(r1)
        mtlr r0
        addi r1, r1, 0x80
        b 0x%08X
    spawn_table:
    """ % (SPAWN, UPDATE_REST))
    assert len(SPAWNS) == 4
    for k, mode in SPAWNS:
        a.asm(".word 0x%X\n.word %d" % (k, mode))
    words = a.words()
    assert CAVE + 4 * len(words) <= DATA, 'field cave too big'
    return a, words


def data_words():
    return [0, 0, 0, 0] + [struct.unpack('>I', struct.pack('>f', v))[0] for v in (1.0, -1.0, DX, DY)]


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000
    return 0x48000000 | (off & 0x03FFFFFC) | (1 if link else 0)


def args():
    a, words = assemble()
    out = ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (DATA + 4 * i, w) for i, w in enumerate(data_words())]
    out.append('0x%08X=0x%08X' % (SITE_A, branch(SITE_A, a.addr('cave_a'))))
    out.append('0x%08X=0x%08X' % (SITE_B, branch(SITE_B, a.addr('cave_b'))))
    out.append('0x%08X=0x%08X' % (SITE_C, branch(SITE_C, a.addr('cave_c'), True)))
    out.append('0x%08X=0x%08X' % (SITE_D, branch(SITE_D, a.addr('cave_d'), True)))
    return out


def configure(name):
    """switch the enemy set ('smashrun' / 'minions') for assemble() / args()"""
    global ENEMIES, SPAWNS, REQUESTS, KINDS
    ENEMIES = name
    SPAWNS, REQUESTS = ENEMY_SETS[name]
    KINDS = tuple(k for k, _m in SPAWNS)


def main():
    if '--minions' in sys.argv:
        sys.argv.remove('--minions')
        configure('minions')
    if len(sys.argv) == 1:
        print(' '.join(args()))
        return
    import rpx_patch
    src, dst = sys.argv[1:3]
    d, _shoff, _ent, secs = rpx_patch.load(src)
    a, words = assemble()
    for site, want in ((SITE_A, WORD_A), (SITE_B, WORD_B), (SITE_C, WORD_C), (SITE_D, WORD_D)):
        got = rpx_patch.read_u32(d, secs, site)
        assert got == want or got >> 26 == 18, '0x%08X holds 0x%08X, expected 0x%08X' % (site, got, want)
    for addr in range(CAVE, LIMIT, 4):
        w = rpx_patch.read_u32(d, secs, addr)
        assert w == 0, 'cave space 0x%08X not free (0x%08X)' % (addr, w)
    sys.argv = ['rpx_patch.py', src, dst] + args()
    rpx_patch.main()


if __name__ == '__main__':
    main()
