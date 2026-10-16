#!/usr/bin/env python3
"""Builds the "copy ability after 12 star missile hits" RPX patch for Kirby.

Prints `ADDR=VALUE` words for tools/rpx_patch.py:
  python3 tools/rpx_patch.py cross_f.rpx out.rpx $(python3 tools/starcopy_cave.py)

Two caves in an unreferenced Havok function (0x037ED898 "TtrcCapsule", 0xEA8 bytes):

STAR CAVE (CAVE1), runs in the star's update. Hook: the star specializer's custom
BattleObject command handler (vtable +0x54, 0x02B037B0, only used by Kirby's star; it was
`li r3,0; blr`) becomes `b CAVE1`. A star's MSC `BattleObject(cmd)` with cmd > 0x15 lands
there with r3 = specializer, r4 = weapon, r5 = message (command value = ***(msg+8)).
For command MAGIC only (see build_star):
  1. owner = *(weapon+0x1BF8); must exist and resolve to Kirby (kind 8) -> Kirby's accessor
  2. target = newest collision record of the star's hitbox 0:
     AM = *(*(weapon+0xC)+0x50); node = *(*(AM+0x14)+0x128); id = *(node+0x18)
     (BattleObject: +0 id, +4 kind, +0xC module accessor; accessor +0x28 WorkModule,
     +0x50 AttackModule); it must exist and resolve to a valid fighter -> kind, costume
  3. count = Kirby int COUNTER + 1. At THRESHOLD (and the target isn't a Kirby): store
     PEND_KIND = kind + 1 and PEND_COSTUME = costume in Kirby's ints, count = 0. Store count.
  4. Report the result to Kirby's DEBUG_INT (Kirby's MSC shows it in debug mode).
  It does NOT grant the copy: copy_grant crashed when called from the star's update.
  Returns 0 (like the stub it replaces). Writing a result to message+0xC (what MSC's
  BattleObject returns) crashed the game, so results go through Kirby's ints instead.

KIRBY CAVE (CAVE2), runs in Kirby's own update. Hook: case 0x409 of Kirby's BattleObject
command dispatcher (0x02EF90D8; 0x409 is unused by Kirby's MSC) becomes `b CAVE2`. There
r31 = Kirby's module accessor. If PEND_KIND > 0: clear it and
copy_grant(spec(8), kirby, PEND_COSTUME, PEND_KIND - 1, 1), like the swallow code
(0x0279666C). Then the dispatcher's normal epilogue. Kirby's MSC main loop calls
BattleObject(0x409) while PEND_KIND > 0.
"""
import struct
import sys

HOOK1 = 0x02B037B0     # star specializer custom command handler (vtable +0x54)
HOOK2 = 0x02EF94E4     # Kirby command dispatcher, case 0x409
HOOK2_RET = 0x02EF9688 # dispatcher epilogue
CAVE = 0x037ED898
CAVE_MAX = 0xEA8
CAVE1 = CAVE
CAVE2 = CAVE + 0x800
MAGIC = 0x1F4          # star MSC: BattleObject(0x1F4) on hit
COUNTER = 0x1000009D   # Kirby ints in the copy range 0x83-0xA0 (copy_grant clears them when it
PEND_KIND = 0x1000009E # grants; the pending copy is read before that). 0x93-0xA0 aren't used by
PEND_COSTUME = 0x1000009B  # Kirby's MSC. 0xA8/0xAA/0xAC didn't work: writes there were lost, so
                       # Kirby's int table probably ends at 0xA6 (the star's ID is stored there).
THRESHOLD = 12

RESOLVE = 0x02BF2108   # (manager, &handle, object id, 0)
EXISTS = 0x02BF3D8C    # (manager, object id) -> 1 if the object exists and is alive
VALID = 0x02BEF61C     # (&handle) -> bool
CATEGORY = 0x02BEF5F4  # (&handle) -> 0 = fighter
KIND = 0x02BEF604      # (&handle) -> fighter kind
COSTUME = 0x02BEF610   # (&handle) -> value copy_grant takes as r5
ACCESSOR = 0x02BEF5DC  # (&handle) -> module accessor
GETSPEC = 0x02E669F0   # (r3, kind) -> fighter specializer
COPYGRANT = 0x02EFCD8C # (spec, kirby accessor, costume, kind, 1)

# Data addresses are absolute, as the game's own code uses them (lis + lwz/addi; data sits at
# its link address). No `bl +4; mflr` position tricks: Cemu's recompiler treats bl as a call
# that must return, and an unbalanced one froze/crashed the emulator.
ADDR_MANAGER = 0x102F6C30  # object manager pointer (0x02C09C5C: lis r30,0x102f / lwz r3,0x6c30(r30))
ADDR_GUARD = 0x10493140    # static guard word (0x02796680)
ADDR_SPECARG = 0x104D1632  # r3 for GETSPEC (0x02796698)

# WorkModule vtable: +0x84 get_int(id), +0x8C set_int(value, id) (checked against the game).
WM_GET_INT = 0x84
WM_SET_INT = 0x8C


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
def andi_(ra, rs, v): return D(28, rs, ra, v)


MFLR_R0 = 0x7C0802A6
MTLR_R0 = 0x7C0803A6
BCTRL = 0x4E800421
BLR = 0x4E800020
COND = {"beq": (12, 2), "bne": (4, 2), "blt": (12, 0), "bge": (4, 0), "ble": (4, 1), "bgt": (12, 1)}


class Asm:
    def __init__(self, base):
        self.base = base
        self.code = []
        self.labels = {}

    def emit(self, x): self.code.append(x)
    def label(self, n): self.labels[n] = len(self.code)

    def load_addr(self, rd, addr):
        self.emit(lis(rd, ((addr + 0x8000) >> 16) & 0xFFFF)); self.emit(addi(rd, rd, addr & 0xFFFF))

    def load_imm32(self, rd, v):
        self.emit(lis(rd, v >> 16)); self.emit(ori(rd, rd, v & 0xFFFF))

    def wm_call(self, acc_reg, slot, args):
        """WorkModule(acc_reg)->slot(args...). args: list of (reg, emitter) run after r3 is set."""
        self.emit(lwz(3, 0x28, acc_reg)); self.emit(lwz(12, 0, 3)); self.emit(lwz(12, slot, 12))
        self.emit(mtctr(12))
        for fn in args:
            fn()
        self.emit(BCTRL)

    def get_int(self, acc_reg, ident):
        self.wm_call(acc_reg, WM_GET_INT, [lambda: self.load_imm32(4, ident)])

    def set_int(self, acc_reg, value_reg, ident):
        self.wm_call(acc_reg, WM_SET_INT, [lambda: self.emit(mr(4, value_reg)),
                                           lambda: self.load_imm32(5, ident)])

    def words(self):
        out = []
        for i, x in enumerate(self.code):
            pc = self.base + 4 * i
            if isinstance(x, tuple):
                kind, arg = x
                if kind in ("bl", "babs"):
                    off = arg - pc
                    assert -0x2000000 <= off < 0x2000000
                    out.append((18 << 26) | (off & 0x3FFFFFC) | (1 if kind == "bl" else 0))
                elif kind == "b":
                    off = 4 * self.labels[arg] - 4 * i
                    out.append((18 << 26) | (off & 0x3FFFFFC))
                else:
                    off = 4 * self.labels[arg] - 4 * i
                    assert -0x8000 <= off < 0x8000
                    bo, bi = COND[kind]
                    out.append((16 << 26) | (bo << 21) | (bi << 16) | (off & 0xFFFC))
            else:
                out.append(x & 0xFFFFFFFF)
        return out


STAGES = ["o", "n", "r", "4a", "4"]
DEBUG_INT = 0x1000009C  # Kirby int: the star cave's last result (Kirby's MSC hops that many times)


def build_star(stage="4"):
    """Star cave. stage o = find the owner Kirby and report 7, nothing else; n = also walk to
    the newest hit record but don't read it (report 1-6, or 7); r = also read the
    hit record (report 1/2, or 7 when a record is there); 4a = count the hits but never hand
    over a copy; 4 = full.
    Finds the owner Kirby first, then reports its result to Kirby's DEBUG_INT:
    1 star's accessor bad, 2 attack module bad, 3 hit records off, 4 record array bad,
    5 no record, 6 record node bad, 7 record found (stage r), 8 target doesn't exist,
    9 target isn't a valid fighter, 10 hit counted, 11 copy handed over (12th hit).
    If the owner Kirby can't be found nothing is reported."""
    upto = STAGES.index(str(stage))
    a = Asm(CAVE1)
    e = a.emit

    def lookup(id_reg, handle_off, fail):
        """Resolve object id_reg into the handle at handle_off(r1), only if it exists
        (the game's callers check with EXISTS first). Uses r3-r6."""
        a.load_addr(3, ADDR_MANAGER); e(lwz(3, 0, 3))
        e(mr(4, id_reg)); e(("bl", EXISTS)); e(cmpwi(3, 0)); e(("beq", fail))
        a.load_addr(3, ADDR_MANAGER); e(lwz(3, 0, 3))
        e(addi(4, 1, handle_off)); e(mr(5, id_reg)); e(li(6, 0)); e(("bl", RESOLVE))

    e(lwz(6, 8, 5)); e(lwz(6, 0, 6)); e(lwz(6, 0, 6))  # command value
    e(cmplwi(6, MAGIC)); e(("bne", "ret0"))
    e(stwu(1, -0x60, 1)); e(MFLR_R0); e(stw(0, 0x64, 1)); e(stmw(26, 0x40, 1))
    e(mr(31, 4))                                      # r31 = weapon
    # 1. owner Kirby -> r27 = Kirby's accessor
    e(lwz(30, 0x1BF8, 31))                            # r30 = owner id
    lookup(30, 0x20, "out")
    e(addi(3, 1, 0x20)); e(("bl", VALID)); e(cmpwi(3, 0)); e(("beq", "out"))
    e(addi(3, 1, 0x20)); e(("bl", KIND)); e(cmpwi(3, 8)); e(("bne", "out"))
    e(addi(3, 1, 0x20)); e(("bl", ACCESSOR)); e(mr(27, 3))
    e(cmpwi(27, 0)); e(("beq", "out"))
    e(stw(27, 0x30, 1))                               # keep Kirby's accessor in the frame too
    if upto == 0:
        e(li(26, 7)); e(("b", "report"))
    # 2. target = newest hit record of the star's hitbox 0. Every pointer is range-checked
    #    (heap 0x10000000-0x50000000, 4-aligned) before it's read through.
    def check_ptr(reg, fail):
        e(lis(7, 0x1000)); e(cmplw(reg, 7)); e(("blt", fail))
        e(lis(7, 0x5000)); e(cmplw(reg, 7)); e(("bge", fail))
        e(andi_(7, reg, 3)); e(("bne", fail))
    e(lwz(3, 0xC, 31)); check_ptr(3, "f1")             # module accessor (BattleObject +0xC, 0x02BEF5DC)
    e(lwz(3, 0x50, 3)); check_ptr(3, "f2")             # AttackModule (accessor +0x50)
    e(lwz(4, 0x4C, 3)); e(cmpwi(4, 0)); e(("beq", "f3"))   # records in use (0x02C09C38)
    e(lwz(6, 0x18, 3)); e(cmpwi(6, 0)); e(("ble", "f4"))   # hitbox count
    e(lwz(4, 0x14, 3)); check_ptr(4, "f4")             # per-hitbox array
    e(lwz(5, 0x128, 4)); e(addi(6, 4, 0x124)); e(cmplw(5, 6)); e(("beq", "f5"))  # empty list
    check_ptr(5, "f6")                                # node
    if upto == 1:                                     # stage n: stop before reading the node
        e(li(26, 7)); e(("b", "report"))
    e(lwz(30, 0x18, 5))                               # r30 = target id
    if upto == 2:
        e(li(26, 7)); e(("b", "report"))
    lookup(30, 0x10, "f8")
    e(addi(3, 1, 0x10)); e(("bl", VALID)); e(cmpwi(3, 0)); e(("beq", "f9"))
    e(addi(3, 1, 0x10)); e(("bl", CATEGORY)); e(cmpwi(3, 0)); e(("bne", "f9"))
    e(addi(3, 1, 0x10)); e(("bl", KIND)); e(mr(29, 3))
    e(addi(3, 1, 0x10)); e(("bl", COSTUME)); e(mr(28, 3))
    # 3. count = get_int(COUNTER) + 1
    e(lwz(27, 0x30, 1))
    a.get_int(27, COUNTER)
    e(addi(26, 3, 1))
    e(cmpwi(26, 0)); e(("bge", "pos")); e(li(26, 1))  # a negative leftover counts as 0
    a.label("pos")
    e(cmpwi(26, THRESHOLD)); e(("blt", "store"))
    e(li(26, 0))
    if upto == 3:
        e(("b", "store"))
    e(cmpwi(29, 8)); e(("beq", "store"))              # target is a Kirby: no copy
    # hand the copy over to Kirby: PEND_KIND = kind + 1, PEND_COSTUME = costume
    e(addi(29, 29, 1))
    a.set_int(27, 29, PEND_KIND)
    a.set_int(27, 28, PEND_COSTUME)
    a.set_int(27, 26, COUNTER)
    e(li(26, 11)); e(("b", "report"))
    a.label("store")
    e(lwz(27, 0x30, 1))
    a.set_int(27, 26, COUNTER)
    e(li(26, 10)); e(("b", "report"))
    for code in (1, 2, 3, 4, 5, 6, 8, 9):
        a.label("f%d" % code)
        e(li(26, code)); e(("b", "report"))
    a.label("report")                                 # r26 = result code -> Kirby's DEBUG_INT
    e(lwz(27, 0x30, 1))                               # reload Kirby's accessor (Cemu crash: r27 looked wrong here)
    a.set_int(27, 26, DEBUG_INT)
    a.label("out")
    e(lmw(26, 0x40, 1)); e(lwz(0, 0x64, 1)); e(MTLR_R0); e(addi(1, 1, 0x60))
    a.label("ret0")
    e(li(3, 0)); e(BLR)
    return a.words()


def build_kirby():
    """Kirby cave: dispatcher case 0x409, r31 = Kirby's accessor. Ends in the epilogue."""
    a = Asm(CAVE2)
    e = a.emit
    e(stwu(1, -0x30, 1)); e(stmw(28, 0x20, 1))
    e(mr(30, 31))                                     # r30 = Kirby's accessor
    a.get_int(30, PEND_KIND); e(mr(29, 3))
    e(cmpwi(29, 0)); e(("ble", "done"))
    a.get_int(30, PEND_COSTUME); e(mr(28, 3))
    e(li(31, 0)); a.set_int(30, 31, PEND_KIND)        # consume it first
    # same static guard and specializer lookup as the swallow code (0x02796680)
    a.load_addr(12, ADDR_GUARD)
    e(lwz(0, 0, 12)); e(cmpwi(0, 0)); e(("bne", "g1"))
    e(li(0, 1)); e(stw(0, 0, 12))
    a.label("g1")
    a.load_addr(3, ADDR_SPECARG); e(li(4, 8)); e(("bl", GETSPEC))
    e(mr(4, 30)); e(mr(5, 28)); e(addi(6, 29, -1)); e(li(7, 1)); e(("bl", COPYGRANT))
    a.label("done")
    e(lmw(28, 0x20, 1)); e(addi(1, 1, 0x30))
    e(("babs", HOOK2_RET))
    return a.words()


def branch(src, dst):
    return (18 << 26) | ((dst - src) & 0x3FFFFFC)


def main():
    stage = "4"
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]
    w1 = build_star(stage)
    w2 = build_kirby()
    assert CAVE1 + 4 * len(w1) <= CAVE2 and CAVE2 + 4 * len(w2) <= CAVE + CAVE_MAX
    # Zero the rest of the dead function: never executed, and zeros compress well, so the
    # recompressed .text section still fits in its original space in the RPX.
    words = [0] * (CAVE_MAX // 4)
    words[0:len(w1)] = w1
    o2 = (CAVE2 - CAVE) // 4
    words[o2:o2 + len(w2)] = w2
    out = ["0x%08X=0x%08X" % (HOOK1, branch(HOOK1, CAVE1)),
           "0x%08X=0x%08X" % (HOOK2, branch(HOOK2, CAVE2))]
    out += ["0x%08X=0x%08X" % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    if "--list" in sys.argv:
        for line in out:
            print(line)
    else:
        print(" ".join(out))


if __name__ == "__main__":
    main()
