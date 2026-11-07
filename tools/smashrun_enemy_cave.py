#!/usr/bin/env python3
"""Smash Run step 2a: Smash Run's own enemies driven by their Master Fortress twins' behaviours
(docs/smash-run-port.md, "Step 2a"). Prints rpx_patch.py args, or patches an RPX (after tools/smashrun_menu.py's and
tools/smashrun_field_cave.py's patches; IN.rpx is read for the twins' motion data sets either way):

  python3 tools/smashrun_enemy_cave.py IN.rpx            the args
  python3 tools/smashrun_enemy_cave.py IN.rpx OUT.rpx    IN with them (checks the hook words first)

The Wii U has behaviours (AI) only for kinds 0x50-0x60. Four of them are Smash Run enemies under another name, the
Master Fortress minions (the same 3DS behaviours): mczakostalfos 0x59, mczakozima 0x5A, mczakoplasmawisp 0x57,
mczakodarios 0x58. The converted 3DS enemies (tools/s3ds_enemy.py: model/enemy/<name>/, motion/enemy/<name>/body/
main.pac, animcmd/enemy/<name>/, sound, effects) have kinds of their own (index in the name table 0x1041A22C):
stalfos 0x30, zima 0x0E, plasmawisp 0x12, darios 0x1D. Each such kind K gets its twin's behaviour:

- F, the behaviour factory 0x02DB94CC (r30 module, r31 kind, r29 variation): 0x02DB9518 `addi r12, r31, -0x50` ->
  a cave that, for the four K, calls the twin's create(module+4 accessor, K, variation) (stalfos 0x026D1DFC, zima
  0x026D6834, plasmawisp 0x026CF4DC, darios 0x026CBA64) and stores it at module+8 as the factory's own cases do
  (create passes K on to the Behavior ctor: K's model / motions / scripts / params); any other kind goes on to the
  factory's switch unchanged.
- T, battle load 0x02D9A454 (before its accessor set-up and smashrun_field_cave.py's resource requests), 0x02D9A468
  `lwz r0, 0x5EC(r31)` -> a cave that, on a Smash Run stage (0x82-0x95), points
  - motion data set table 0x10352610[K] (get_motion_data_set 0x02DC6D68, read by the enemy's accessor set-up
    0x02DA2A3C; kinds below 0x50 have an empty default) at a set built here: the twin's set in its own index order
    (the behaviours name motions by index), each entry's hash the CRC of K's own animation (the stem of its OMO in
    K's main.pac), the twin's flags and script hashsets;
  - article table 0x10352794[K] (0x02DC6D88: the weapons the resource request 0x030BF400 loads and the behaviour
    fires; Plasma Wisp's shots) at the twin's.
  Both tables are .data the cave writes at run time (no relocation to move); the entries stay set afterwards (no
  other mode uses these kinds).
- S, the battle's param load 0x02D9A5EC, 0x02D9A614 `bl 0x02DC67C0` (the param accessor's per-kind load: param
  manager *(0x102F6C00) + 0x60 + 4 * kind, sm category 0x50-0x5A) -> a cave that makes the call, then on a Smash
  Run stage copies the twin's param slot into K's (the enemy's activation 0x02D89CC8 reads [slot]+0x70 and the
  accessor set-up [slot]+0x5C unchecked; the behaviours read their tuning from slot[own kind] or their twin's
  hard-coded slot: the Wii U sm vl layout their code was built for).

Motion data set (layout as the game's): +0 entries*, +4 count, +8..+0x14 0, +0x18 count x 12-byte script hashsets
(init / main / exit script hashes), then the entries {u32 hash, u32 flags}. Entry hash = zlib.crc32(stem, 0xFFFFFFFF),
the stem the OMO's name in the pac without ".omo", case kept (checked: every one of the Wii U mczako sets' entries,
572 entries of the fighters' weapon sets in .data). The twins' sets are those names with "Mczako" inserted
(EnmMczakostalfosBodyMainAttack1 <-> EnmStalfosBodyMainAttack1); stalfos's index 26 is FlinchEnd on the Wii U,
Flinchend in K's pac. The hashsets are the twin's: K's converted scripts (stalfos's attack.bin / effect.bin) carry
the same hashes (checked).

Space: 0x04B85800-0x04B86800 (code, then the sets from SETS), in kind_expand.py's old stale space
(0x04B85800-0x04B877C4: nothing refers to it, docs/boot-training.md), which this clears to zeros up to 0x04B88000
(base_effects_cave.py's), so no stale word sits next to the code.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm, ha, lo  # noqa: E402
import smashrun_field_cave as F  # noqa: E402

CAVE = 0x04B85800
SETS = 0x04B85C00
LIMIT = 0x04B86800
CLEAR = (0x04B85800, 0x04B88000)     # kind_expand.py's old space: stale words, cleared

# (name, Smash Run kind, Wii U twin kind, twin's create)
PAIRS = (
    ('stalfos', 0x30, 0x59, 0x026D1DFC),
    ('zima', 0x0E, 0x5A, 0x026D6834),
    ('plasmawisp', 0x12, 0x57, 0x026CF4DC),
    ('darios', 0x1D, 0x58, 0x026CBA64),
)
# K's animations: Enm<Name>BodyMain<suffix>.omo in motion/enemy/<name>/body/main.pac (tools/s3ds_enemy.py, the 3DS's
# names); the twin's are EnmMczako<name>BodyMain<suffix> (WIIU_SUFFIX where the Wii U renamed one)
MOTIONS = {
    'stalfos': ('Attack1 Attack1end Attack2 Attack2end AttackHold DamageFall DamageFly DamageStart DownBound '
                'DownBoundEnd DownLoop DownWait Fall Fightingback Fightingcancell Fightingmove Fightingpose '
                'Fightingturn Fightingwait Flinch FlinchStart Flinchend Guardreact Jumpattack Jumpattacklanding '
                'Landiing Move Step Steplanding Turn').split(),
    'zima': 'Damage DamageFall DamageFly DamageStart DownBound DownBoundEnd DownLoop DownWait Move Turn Wait'.split(),
    'plasmawisp': ('AirTurn Cannon CannonHold Damage DamageFall DamageFly DamageStart DownBound DownBoundEnd '
                   'DownLoop DownWait Float Laser LaserHold Needle NeedleHold').split(),
    'darios': 'DamageFall DamageFly DamageStart DownBound DownBoundEnd DownLoop DownStandU DownWait Turn'.split(),
}
WIIU_SUFFIX = {'stalfos': {'Flinchend': 'FlinchEnd'}}

MOTION_SETS = 0x10352610        # get_motion_data_set 0x02DC6D68: [kind] (< 0x61)
ARTICLE_SETS = 0x10352794       # 0x02DC6D88: [kind]
PARAM_MGR = 0x102F6C00          # *: the enemy param manager, kind slots at +0x60
SLOTS = 0x60
PARAM_LOAD = 0x02DC67C0

SITE_F, WORD_F = 0x02DB9518, 0x399FFFB0      # addi r12, r31, -0x50
FACTORY_SWITCH, FACTORY_END = 0x02DB951C, 0x02DB96E0
SITE_T, WORD_T = 0x02D9A468, 0x801F05EC      # lwz r0, 0x5EC(r31)
SITE_S = 0x02D9A614                          # bl 0x02DC67C0


def branch(src, dst, link=False):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000
    return 0x48000000 | (off & 0x03FFFFFC) | (1 if link else 0)


WORD_S = branch(SITE_S, PARAM_LOAD, True)


def branch_target(src, word):
    off = word & 0x03FFFFFC
    return src + (off - 0x4000000 if off & 0x2000000 else off)


def motion_hash(stem):
    return zlib.crc32(stem.encode(), 0xFFFFFFFF)


def stem(name, suffix, twin=False):
    if twin:
        return 'EnmMczako%sBodyMain%s' % (name, WIIU_SUFFIX.get(name, {}).get(suffix, suffix))
    return 'Enm%sBodyMain%s' % (name.capitalize(), suffix)


# ---------------------------------------------------------------- reading the executable
class Image:
    """the RPX's sections, read once"""

    def __init__(self, path):
        import rpx_patch
        self.d, _shoff, _ent, self.secs = rpx_patch.load(path)
        self.mem = []
        for s in self.secs:
            if s[1] == 1 and s[3] and s[5]:
                self.mem.append((s[3], bytes(rpx_patch.section_data(self.d, s))))

    def u32(self, addr):
        for base, data in self.mem:
            if base <= addr < base + len(data):
                return struct.unpack('>I', data[addr - base:addr - base + 4])[0]
        raise KeyError(hex(addr))


def read_set(img, kind):
    """(entries [(hash, flags)], hashsets [(a, b, c)], the four words +8..+0x14) of the game's set for kind"""
    s = img.u32(MOTION_SETS + 4 * kind)
    e, n = img.u32(s), img.u32(s + 4)
    entries = [(img.u32(e + 8 * i), img.u32(e + 8 * i + 4)) for i in range(n)]
    hashsets = [tuple(img.u32(s + 0x18 + 12 * i + 4 * j) for j in range(3)) for i in range(n)]
    return entries, hashsets, [img.u32(s + 8 + 4 * i) for i in range(4)]


def map_set(name, twin_entries):
    """K's stems in the twin's index order"""
    by_hash = {motion_hash(stem(name, sfx, True)): sfx for sfx in MOTIONS[name]}
    out = []
    for i, (h, _flags) in enumerate(twin_entries):
        assert h in by_hash, '%s: the twin\'s entry %d (0x%08X) has no animation in K\'s pac' % (name, i, h)
        out.append(stem(name, by_hash[h]))
    return out


def build_sets(img):
    """{name: (address, words, stems)}: K's sets laid out from SETS"""
    out = {}
    addr = SETS
    for name, _k, twin, _create in PAIRS:
        entries, hashsets, extra = read_set(img, twin)
        assert extra == [0, 0, 0, 0], extra
        stems = map_set(name, entries)
        n = len(entries)
        words = [addr + 0x18 + 12 * n, n, 0, 0, 0, 0]
        for hs in hashsets:
            words += list(hs)
        for st, (_h, flags) in zip(stems, entries):
            words += [motion_hash(st), flags]
        out[name] = (addr, words, stems)
        addr = (addr + 4 * len(words) + 0xF) & ~0xF
    assert addr <= LIMIT, 'sets too big'
    return out


# ---------------------------------------------------------------- code
def assemble(sets):
    a = Asm(CAVE)
    # F: the factory (r30 module, r31 kind, r29 variation)
    a.asm("cave_f:")
    for i, (_n, k, _t, _c) in enumerate(PAIRS):
        a.asm("cmpwi r31, 0x%X\nbeq f_%d" % (k, i))
    a.asm("""
        addi r12, r31, -0x50
        b 0x%08X
    """ % FACTORY_SWITCH)
    for i, (_n, _k, _t, create) in enumerate(PAIRS):
        a.asm("""
    f_%d:
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        b f_call
        """ % (i, create >> 16, create & 0xFFFF))
    a.asm("""
    f_call:
        mtctr r12                   # the creates are out of bl reach
        lwz r3, 4(r30)
        mr r4, r31
        mr r5, r29
        bctrl
        stw r3, 8(r30)
        b 0x%08X
    """ % FACTORY_END)
    # T: the motion data set and article tables (r31 = the EnemyManager; r3-r12 free here)
    a.asm("cave_t:")
    F.sr_check(a)
    a.asm("bgt t_done")
    for name, k, twin, _c in PAIRS:
        sa = sets[name][0]
        a.asm("""
        lis r11, 0x%04X
        addi r11, r11, %d
        lis r12, 0x%04X
        stw r11, %d(r12)
        lis r12, 0x%04X
        lwz r11, %d(r12)
        lis r12, 0x%04X
        stw r11, %d(r12)
        """ % (ha(sa), slo(sa), ha(MOTION_SETS + 4 * k), slo(MOTION_SETS + 4 * k),
               ha(ARTICLE_SETS + 4 * twin), slo(ARTICLE_SETS + 4 * twin),
               ha(ARTICLE_SETS + 4 * k), slo(ARTICLE_SETS + 4 * k)))
    a.asm("""
    t_done:
        lwz r0, 0x5EC(r31)
        b 0x%08X
    """ % (SITE_T + 4))
    # S: the param load, then the slots
    a.asm("""
    cave_s:
        mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        bl 0x%08X
        stw r3, 0x10(r1)
    """ % PARAM_LOAD)
    F.sr_check(a)
    a.asm("""
        bgt s_done
        lis r12, 0x%04X
        lwz r12, %d(r12)
        cmpwi r12, 0
        beq s_done
    """ % (ha(PARAM_MGR), slo(PARAM_MGR)))
    for _n, k, twin, _c in PAIRS:
        a.asm("lwz r11, 0x%X(r12)\nstw r11, 0x%X(r12)" % (SLOTS + 4 * twin, SLOTS + 4 * k))
    a.asm("""
    s_done:
        lwz r3, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
    """)
    words = a.words()
    assert CAVE + 4 * len(words) <= SETS, 'enemy cave code too big'
    return a, words


def slo(v):
    v = lo(v)
    return v - 0x10000 if v & 0x8000 else v


def patches(img):
    """{address: word}: code, sets, the hooks, and zeros over the rest of CLEAR"""
    sets = build_sets(img)
    a, words = assemble(sets)
    out = {}
    for addr in range(CLEAR[0], CLEAR[1], 4):
        out[addr] = 0
    for i, w in enumerate(words):
        out[CAVE + 4 * i] = w
    for addr, ws, _stems in sets.values():
        for i, w in enumerate(ws):
            out[addr + 4 * i] = w
    out[SITE_F] = branch(SITE_F, a.addr('cave_f'))
    out[SITE_T] = branch(SITE_T, a.addr('cave_t'))
    out[SITE_S] = branch(SITE_S, a.addr('cave_s'), True)
    return out, a, sets


def args(img, only_changed=True):
    out, _a, _sets = patches(img)
    res = ['grow:0x%08X' % LIMIT]
    for addr, w in sorted(out.items()):
        if only_changed and CLEAR[0] <= addr < CLEAR[1] and w == 0:
            try:
                if img.u32(addr) == 0:
                    continue
            except KeyError:
                continue
        res.append('0x%08X=0x%08X' % (addr, w))
    return res


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    img = Image(sys.argv[1])
    if len(sys.argv) == 2:
        print(' '.join(args(img)))
        return
    import rpx_patch
    for site, want in ((SITE_F, WORD_F), (SITE_T, WORD_T), (SITE_S, WORD_S)):
        got = img.u32(site)
        assert got == want or (got >> 26 == 18 and CAVE <= branch_target(site, got) < SETS), \
            '0x%08X holds 0x%08X, expected 0x%08X' % (site, got, want)
    if img.u32(F.SITE_C) >> 26 != 18:       # smashrun_field_cave.py's requests load K's resources
        print('warning: tools/smashrun_field_cave.py is not applied: nothing loads or spawns the Smash Run kinds',
              file=sys.stderr)
    sys.argv = ['rpx_patch.py', sys.argv[1], sys.argv[2]] + args(img)
    rpx_patch.main()


if __name__ == '__main__':
    main()
