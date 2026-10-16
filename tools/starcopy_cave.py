#!/usr/bin/env python3
"""Builds the "copy ability after 12 star missile hits" RPX patch for Kirby.

Prints `ADDR=VALUE` words for tools/rpx_patch.py:
  python3 tools/rpx_patch.py cross_f.rpx out.rpx $(python3 tools/starcopy_cave.py)

How it works (see docs/native-notes.md, "Star missile hits" / "Kirby copy abilities"):
- Hook: the star missile specializer's custom BattleObject command handler (vtable +0x54,
  0x02B037B0, only used by Kirby's star; it was `li r3,0; blr`) becomes `b CAVE`.
  A star's MSC `BattleObject(cmd)` with cmd > 0x15 lands there with r3 = specializer,
  r4 = weapon, r5 = message (command value = ***(msg+8)).
- CAVE (overwrites an unreferenced Havok function, 0x037ED898 "TtrcCapsule", 0xEA8 bytes):
  for command MAGIC only:
    1. target = newest collision record of the star's hitbox 0:
       AM = *(*(weapon+0xC)+0x50); node = *(*(AM+0x14)+0x128); id = *(node+0x18)
       (BattleObject: +0 id, +4 kind, +0xC module accessor; accessor +0x28 WorkModule, +0x50 AttackModule)
    2. resolve the target; must be a valid fighter -> kind, costume value
    3. owner = *(weapon+0x1BF8); must resolve to Kirby (kind 8) -> Kirby's accessor
    4. count = Kirby int COUNTER + 1; at THRESHOLD: copy_grant(spec(8), kirby, costume, kind, 1)
       (skipped if the target is a Kirby) and count = 0; store count.
  Always returns 0 (like the stub it replaces).
"""
import struct
import sys

HOOK = 0x02B037B0
CAVE = 0x037ED898
CAVE_MAX = 0xEA8
MAGIC = 0x1F4          # star MSC: BattleObject(0x1F4) on hit
COUNTER = 0x1000009D   # Kirby instance int (unused by MSC and native code)
THRESHOLD = 12

RESOLVE = 0x02BF2108   # (manager, &handle, object id, 0)
VALID = 0x02BEF61C     # (&handle) -> bool
CATEGORY = 0x02BEF5F4  # (&handle) -> 0 = fighter
KIND = 0x02BEF604      # (&handle) -> fighter kind
COSTUME = 0x02BEF610   # (&handle) -> value copy_grant takes as r5
ACCESSOR = 0x02BEF5DC  # (&handle) -> module accessor
GETSPEC = 0x02E669F0   # (r3, kind) -> fighter specializer
COPYGRANT = 0x02EFCD8C # (spec, kirby accessor, costume, kind, 1)

EXISTS = 0x02BF3D8C    # (manager, object id) -> 1 if the object exists and is alive

# Data addresses are absolute, as the game's own code uses them (lis + lwz/addi; data sits at
# its link address). No `bl +4; mflr` position tricks: Cemu's recompiler treats bl as a call
# that must return, and an unbalanced one froze/crashed the emulator.
ADDR_MANAGER = 0x102F6C30  # object manager pointer (0x02C09C5C: lis r30,0x102f / lwz r3,0x6c30(r30))
ADDR_GUARD = 0x10493140    # static guard word (0x02796680)
ADDR_SPECARG = 0x104D1632  # r3 for GETSPEC (0x02796698)


def D(op, rd, ra, imm):
    return (op << 26) | (rd << 21) | (ra << 16) | (imm & 0xFFFF)


def lwz(rd, d, ra): return D(32, rd, ra, d)
def stw(rs, d, ra): return D(36, rs, ra, d)
def stwu(rs, d, ra): return D(37, rs, ra, d)
def lmw(rd, d, ra): return D(46, rd, ra, d)
def stmw(rs, d, ra): return D(47, rs, ra, d)
def addi(rd, ra, v): return D(14, rd, ra, v)
def li(rd, v): return addi(rd, 0, v)
def lis(rd, v): return D(15, rd, 0, v)
def ori(ra, rs, v): return D(24, rs, ra, v)
def cmpwi(ra, v): return D(11, 0, ra, v)
def cmplwi(ra, v): return D(10, 0, ra, v)
def cmplw(ra, rb): return (31 << 26) | (ra << 16) | (rb << 11) | (32 << 1)
def mr(ra, rs): return (31 << 26) | (rs << 21) | (ra << 16) | (rs << 11) | (444 << 1)
def mtctr(rs): return (31 << 26) | (rs << 21) | (0x120 << 11) | (467 << 1)
def mflr(rd): return (31 << 26) | (rd << 21) | (0x100 << 11) | (339 << 1)
def addis(rd, ra, v): return D(15, rd, ra, v)
def rlwinm(ra, rs, sh, mb, me): return (21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1)
def extsh(ra, rs): return (31 << 26) | (rs << 21) | (ra << 16) | (922 << 1)
def add(rd, ra, rb): return (31 << 26) | (rd << 21) | (ra << 16) | (rb << 11) | (266 << 1)


MFLR_R0 = 0x7C0802A6
MTLR_R0 = 0x7C0803A6
BCTRL = 0x4E800421
BLR = 0x4E800020
COND = {"beq": (12, 2), "bne": (4, 2), "blt": (12, 0), "bge": (4, 0), "ble": (4, 1), "bgt": (12, 1)}


STAGES = ["1", "1a", "1b", "1c", "2", "3", "4a", "4b", "4"]


def build(stage="4"):
    """stage (for crash bisecting), each one runs a bit more than the one before:
    1  = return right after the command check
    1a = also set up / tear down the stack frame (no reads, no calls)
    1b = also read the target id from the star's hit records (no calls)
    1c = also resolve the target (one call)
    2  = also check / read the target (valid, fighter, kind, costume)
    3  = also find the owner Kirby
    4a = also count the hit (read + write Kirby's counter), never grant a copy
    4b = also get the copy specializer at the 12th hit, but don't grant the copy
    4  = full."""
    stage = str(stage)
    upto = STAGES.index(stage)
    code = []   # entries: int word, or (kind, arg) to resolve
    labels = {}

    def emit(x): code.append(x)
    def label(n): labels[n] = len(code)

    def load_addr(rd, addr):
        """rd = addr (absolute)."""
        emit(lis(rd, ((addr + 0x8000) >> 16) & 0xFFFF)); emit(addi(rd, rd, addr & 0xFFFF))

    def lookup(id_reg, handle_off):
        """Resolve object id_reg (r30/r31-safe) into the handle at handle_off(r1), only if it
        exists (the game's callers check with EXISTS first). Uses r3-r6."""
        load_addr(3, ADDR_MANAGER); emit(lwz(3, 0, 3))
        emit(mr(4, id_reg)); emit(("bl", EXISTS)); emit(cmpwi(3, 0)); emit(("beq", "out"))
        load_addr(3, ADDR_MANAGER); emit(lwz(3, 0, 3))
        emit(addi(4, 1, handle_off)); emit(mr(5, id_reg)); emit(li(6, 0)); emit(("bl", RESOLVE))

    emit(lwz(6, 8, 5)); emit(lwz(6, 0, 6)); emit(lwz(6, 0, 6))  # command value
    emit(cmplwi(6, MAGIC)); emit(("bne", "ret0"))
    if upto == 0:
        emit(("b", "ret0"))
    emit(stwu(1, -0x60, 1)); emit(MFLR_R0); emit(stw(0, 0x64, 1)); emit(stmw(26, 0x40, 1))
    emit(mr(31, 4))                                   # r31 = weapon
    if upto == 1:
        emit(("b", "out"))
    emit(lwz(3, 0xC, 31))                             # module accessor (BattleObject +0xC, see 0x02BEF5DC)
    emit(cmpwi(3, 0)); emit(("beq", "out"))
    emit(lwz(3, 0x50, 3))                             # AttackModule (accessor +0x50)
    emit(cmpwi(3, 0)); emit(("beq", "out"))
    emit(lwz(4, 0x4C, 3)); emit(cmpwi(4, 0)); emit(("beq", "out"))   # records in use (0x02C09C38)
    emit(lwz(4, 0x14, 3)); emit(cmpwi(4, 0)); emit(("beq", "out"))
    emit(lwz(6, 0x18, 3)); emit(cmpwi(6, 0)); emit(("ble", "out"))
    emit(lwz(5, 0x128, 4)); emit(addi(6, 4, 0x124)); emit(cmplw(5, 6)); emit(("beq", "out"))
    emit(cmpwi(5, 0)); emit(("beq", "out"))           # null node (0x02C09C94)
    emit(lwz(30, 0x18, 5))                            # r30 = target id
    if upto == 2:
        emit(("b", "out"))
    # resolve target (exists check first)
    lookup(30, 0x10)
    if upto == 3:
        emit(("b", "out"))
    emit(addi(3, 1, 0x10)); emit(("bl", VALID)); emit(cmpwi(3, 0)); emit(("beq", "out"))
    emit(addi(3, 1, 0x10)); emit(("bl", CATEGORY)); emit(cmpwi(3, 0)); emit(("bne", "out"))
    emit(addi(3, 1, 0x10)); emit(("bl", KIND)); emit(mr(29, 3))
    emit(addi(3, 1, 0x10)); emit(("bl", COSTUME)); emit(mr(28, 3))
    if upto == 4:
        emit(("b", "out"))
    # owner Kirby
    emit(lwz(30, 0x1BF8, 31))                         # r30 = owner id (target id no longer needed)
    lookup(30, 0x20)
    emit(addi(3, 1, 0x20)); emit(("bl", VALID)); emit(cmpwi(3, 0)); emit(("beq", "out"))
    emit(addi(3, 1, 0x20)); emit(("bl", KIND)); emit(cmpwi(3, 8)); emit(("bne", "out"))
    emit(addi(3, 1, 0x20)); emit(("bl", ACCESSOR)); emit(mr(27, 3))
    if upto == 5:
        emit(("b", "out"))
    # count = get_int(COUNTER) + 1
    emit(lwz(3, 0x28, 27)); emit(lwz(12, 0, 3)); emit(lwz(12, 0x84, 12)); emit(mtctr(12))
    emit(lis(4, COUNTER >> 16)); emit(ori(4, 4, COUNTER & 0xFFFF)); emit(BCTRL)
    emit(addi(26, 3, 1))
    if upto == 6:
        emit(("b", "store"))
    emit(cmpwi(26, THRESHOLD)); emit(("blt", "store"))
    emit(li(26, 0))
    emit(cmpwi(29, 8)); emit(("beq", "store"))         # target is a Kirby: no copy
    load_addr(12, ADDR_GUARD)
    emit(lwz(0, 0, 12)); emit(cmpwi(0, 0)); emit(("bne", "g1"))
    emit(li(0, 1)); emit(stw(0, 0, 12))                # same static guard as the swallow code
    label("g1")
    load_addr(3, ADDR_SPECARG); emit(li(4, 8)); emit(("bl", GETSPEC))
    if upto == 7:
        emit(("b", "store"))
    emit(mr(4, 27)); emit(mr(5, 28)); emit(mr(6, 29)); emit(li(7, 1)); emit(("bl", COPYGRANT))
    label("store")
    emit(lwz(3, 0x28, 27)); emit(lwz(12, 0, 3)); emit(lwz(12, 0x8C, 12)); emit(mtctr(12))
    emit(mr(4, 26)); emit(lis(5, COUNTER >> 16)); emit(ori(5, 5, COUNTER & 0xFFFF)); emit(BCTRL)
    label("out")
    emit(lmw(26, 0x40, 1)); emit(lwz(0, 0x64, 1)); emit(MTLR_R0); emit(addi(1, 1, 0x60))
    label("ret0")
    emit(li(3, 0)); emit(BLR)

    words = []
    for i, x in enumerate(code):
        pc = CAVE + 4 * i
        if isinstance(x, tuple):
            kind, arg = x
            if kind == "bl":
                off = arg - pc
                assert -0x2000000 <= off < 0x2000000
                words.append((18 << 26) | (off & 0x3FFFFFC) | 1)
            elif kind == "b":
                off = 4 * labels[arg] - 4 * i
                words.append((18 << 26) | (off & 0x3FFFFFC))
            else:
                off = 4 * labels[arg] - 4 * i
                assert -0x8000 <= off < 0x8000
                bo, bi = COND[kind]
                words.append((16 << 26) | (bo << 21) | (bi << 16) | (off & 0xFFFC))
        else:
            words.append(x & 0xFFFFFFFF)
    assert len(words) * 4 <= CAVE_MAX
    return words


def main():
    stage = "4"
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]
    words = build(stage)
    hook_off = CAVE - HOOK
    hook = (18 << 26) | (hook_off & 0x3FFFFFC)
    # Zero the rest of the dead function: never executed, and zeros compress well, so the
    # recompressed .text section still fits in its original space in the RPX.
    words = words + [0] * (CAVE_MAX // 4 - len(words))
    out = ["0x%08X=0x%08X" % (HOOK, hook)]
    out += ["0x%08X=0x%08X" % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    if "--list" in sys.argv:
        for line in out:
            print(line)
    else:
        print(" ".join(out))


if __name__ == "__main__":
    main()
