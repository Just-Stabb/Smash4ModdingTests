#!/usr/bin/env python3
"""Copy-ability trait stat boosts for Kirby: prints rpx_patch.py args (ADDR=VALUE words).

  python3 tools/rpx_patch.py IN.rpx OUT.rpx <other patches> $(python3 tools/kirby_stat_cave.py)
  python3 tools/kirby_stat_cave.py --table     (the profile table's words only)

Every fighter stat ("fighter_param", WorkModule category 3, e.g. 0x03000016 max air speed) is read
through WorkModuleImpl::get_float (0x0200F628, vtable 0x10003224 +0x44), by the native movement code
(walk/run/jump/air kinetics) and by MSC alike. The stats are the character's shared fighter_param
entry, so they can't be changed in place for one Kirby; instead the read is scaled.

The first instruction of get_float (every copy: fighters have their own, HOOKS) branches to CAVE, which does the original read and then, for a
category-3 stat with index < 32, looks at the object's instance int INT_INDEX (0x1000008E):
  - the int array must exist and hold more than INT_INDEX entries (other fighters, weapons, items);
  - the value must be 0x4B49xxxx ("KI", written only by Kirby's MSC, kirby_trait_update);
  - its low 3 bits are a profile number; profile 0 = no change.
The profile picks a (stat mask, multiplier) pair from TABLE; a stat whose bit is set in the mask is
multiplied. Kirby's MSC writes the int every frame from the trait of his current copy ability
(docs/character-traits.md).

Profiles (keep in sync with kirby_trait_profile() in fighters/kirby/kirby.c):
  1 = Rush: x1.25 on walk, dash, run, jump horizontal, air speed / acceleration, fall and fast fall
      speed. Not jump height, gravity, traction or landing lag.
  2 = Overdrive (Kirby's Corrin copy after 3 pummels): the Rush stats x1.25 x1.2 = x1.5.
  3 = Hero's Acceleratle (any fighter writing the marker: fighters/brave/brave.c): walk, dash, run, jump
      horizontal and air speeds x2.

The cave sits in the free part of the dead Havok function used by the other Kirby caves
(starcopy_cave.py zero-fills 0x037ED898-0x037EE740 and moves its relocations away, so this must come
after it on the command line).
"""
import struct
import sys

HOOK = 0x0200F628          # WorkModuleImpl::get_float
# get_float of the WorkModuleImpl subclasses (identical code; fighters use 0x02F1DBE4), all hooked
HOOKS = [HOOK, 0x02BCD8A0, 0x02DA6020, 0x02F1DBE4, 0x03060880]
CAVE = 0x037EE160          # free: 0x037EE15C-0x037EE400 (star cave ends at 0x037EE15C)
LIMIT = 0x037EE400         # CAVE_C (copy_custom_cave.py) starts here
INT_INDEX = 0x8E           # Kirby instance int 0x1000008E (unused by Kirby's MSC; copy_grant clears it)
MAGIC = 0x4B49             # "KI"

# fighter_param indices (Sammi Husky's sheet, docs/resources.md)
WALK = (0x01, 0x02, 0x03)              # walk max additional accel, base walk accel, walk max speed
DASH_RUN = (0x08, 0x09, 0x0A, 0x0B)    # dash initial speed, run max additional accel, base run accel, run max speed
JUMP_H = (0x0D, 0x0F, 0x10)            # added H speed from ground jump, jump H max, initial H speed of air jumps
AIR = (0x14, 0x15, 0x16)               # air max additional accel, base air accel, max air speed
FALL = (0x19, 0x1B)                    # max fall speed, fast fall speed

PROFILES = {
    1: (WALK + DASH_RUN + JUMP_H + AIR + FALL, 1.25),   # Rush
    2: (WALK + DASH_RUN + JUMP_H + AIR + FALL, 1.25 * 1.2),   # Overdrive (Corrin copy): Rush x1.2
    3: (WALK + DASH_RUN + JUMP_H + AIR, 2.0),   # Hero's Acceleratle (fighters/brave/brave.c brave_buff_update;
                                                # Ultimate's speed_up_* x2-2.5, one multiplier here)
}
TABLE_ENTRIES = 8          # profiles 0-7 (the profile is masked to 3 bits); position_vars_cave.py uses the space after


def rlwinm(ra, rs, sh, mb, me, rc=0):
    return (21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1) | rc


def d_form(op, rt, ra, imm):
    return (op << 26) | (rt << 21) | (ra << 16) | (imm & 0xFFFF)


def x_form(rt, ra, rb, xo):
    return (31 << 26) | (rt << 21) | (ra << 16) | (rb << 11) | (xo << 1)


def lwz(rt, d, ra): return d_form(32, rt, ra, d)
def lfs(ft, d, ra): return d_form(48, ft, ra, d)
def cmpwi(ra, imm): return d_form(11, 0, ra, imm)
def cmplwi(ra, imm): return d_form(10, 0, ra, imm)
def andi_(ra, rs, imm): return d_form(28, rs, ra, imm)
def lis(rt, imm): return d_form(15, rt, 0, imm)
def addi(rt, ra, imm): return d_form(14, rt, ra, imm)
def lwzx(rt, ra, rb): return x_form(rt, ra, rb, 23)
def lfsx(ft, ra, rb): return x_form(ft, ra, rb, 535)
def add(rt, ra, rb): return x_form(rt, ra, rb, 266)
def srw(ra, rs, rb): return (31 << 26) | (rs << 21) | (ra << 16) | (rb << 11) | (536 << 1)
def fmuls(fd, fa, fc): return (59 << 26) | (fd << 21) | (fa << 16) | (fc << 6) | (25 << 1)
def b(src, dst): return (18 << 26) | ((dst - src) & 0x3FFFFFC)


BLR = 0x4E800020
BNELR = 0x4C820020   # bclr 4, eq
BEQLR = 0x4D820020   # bclr 12, eq
BLTLR = 0x4D800020   # bclr 12, lt
BGELR = 0x4C800020   # bclr 4, lt


def ha(v): return ((v + 0x8000) >> 16) & 0xFFFF
def lo(v): return v & 0xFFFF


def code(table):
    return [
        # original get_float: f1 = [[[this+8] + cat*4] + 4][index & 0xFFFFFF]
        rlwinm(11, 4, 8, 28, 31),       # r11 = category
        lwz(0, 8, 3),                   # r0 = category table
        rlwinm(10, 11, 2, 0, 29),       # r10 = cat * 4
        lwzx(12, 10, 0),                # r12 = container
        lwz(10, 4, 12),                 # r10 = float array
        rlwinm(12, 4, 2, 6, 29),        # r12 = (index & 0xFFFFFF) * 4
        lfsx(1, 12, 10),                # f1 = value
        # only fighter stats 0x03000000-0x0300001F
        cmpwi(11, 3), BNELR,
        rlwinm(12, 4, 0, 8, 31),        # r12 = index
        cmplwi(12, 32), BGELR,
        # this object's instance int INT_INDEX (ID 0x1000008E: category (id >> 24) & 0xF = 0, as in
        # get_int 0x0200F7F0) must hold the Kirby marker. (The first version read category 1,
        # [table + 4], the status ints, so it never matched.)
        lwzx(11, 0, 0),                 # r11 = category 0 container = [table] (rA = 0: EA = r0)
        cmpwi(11, 0), BEQLR,
        lwz(10, 8, 11),                 # r10 = int count (top 2 bits are flags)
        rlwinm(10, 10, 0, 2, 31),
        cmplwi(10, INT_INDEX + 1), BLTLR,
        lwz(11, 0xC, 11),               # r11 = int array
        cmpwi(11, 0), BEQLR,
        lwz(11, INT_INDEX * 4, 11),     # r11 = value
        rlwinm(10, 11, 16, 16, 31),     # r10 = value >> 16
        cmplwi(10, MAGIC), BNELR,
        andi_(11, 11, 0x7),             # r11 = profile (0-7)
        BEQLR,
        lis(10, ha(table)),
        addi(10, 10, lo(table)),
        rlwinm(11, 11, 3, 0, 28),       # profile * 8
        add(10, 10, 11),                # r10 = entry
        lwz(11, 0, 10),                 # r11 = stat mask
        srw(11, 11, 12),
        andi_(11, 11, 1),
        BEQLR,
        lfs(0, 4, 10),                  # f0 = multiplier
        fmuls(1, 1, 0),
        BLR,
    ]


def words():
    n = len(code(0))
    table = CAVE + n * 4
    table = (table + 7) & ~7
    out = {}
    for i, w in enumerate(code(table)):
        out[CAVE + i * 4] = w
    for p in range(TABLE_ENTRIES):
        mask, mult = 0, 1.0
        if p in PROFILES:
            stats, mult = PROFILES[p]
            for s in stats:
                mask |= 1 << s
        out[table + p * 8] = mask
        out[table + p * 8 + 4] = struct.unpack('>I', struct.pack('>f', mult))[0]
    assert max(out) + 4 <= LIMIT, "cave too long"
    for hook in HOOKS:
        out[hook] = b(hook, CAVE)
    return out


def table_words():
    """the profile table alone: for an executable whose get_float path later caves have changed
    (tools/position_vars_cave.py, acmd_ext_cave.py), e.g. tools/brave_build.py's"""
    w = words()
    n = len(code(0))
    table = (CAVE + n * 4 + 7) & ~7
    return {a: v for a, v in w.items() if table <= a < table + TABLE_ENTRIES * 8}


def main():
    w = table_words() if "--table" in sys.argv else words()
    print(" ".join("0x%08X=0x%08X" % (a, v) for a, v in sorted(w.items())))


if __name__ == "__main__":
    main()
