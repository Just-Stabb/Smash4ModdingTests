#!/usr/bin/env python3
"""Tiny PowerPC assembler for code caves (the subset the caves use).

    a = Asm(0x037EDC78)
    a.asm('''
    start:  lwz r3, 0x28(r12)
            cmpwi r3, 0
            beq done
            b 0x0200F64C        # absolute targets are numbers, local ones are labels
    done:   blr
    ''')
    words = a.words()           # list of 32-bit words, a.labels has label -> address

Comments start with '#' or ';'. `beq.far LABEL` (any condition) is an inverted short branch over a
plain `b`, for targets beyond the 32 KB reach of a conditional branch; `$+8` is pc + 8. `.float X` and `.word X` emit data. Branch targets that parse as
numbers are absolute addresses; anything else is a label. Conditional branches compare cr0 unless a
`crN,` operand comes first. Checked against capstone in tests (see position_vars_cave.py --check).
"""
import re
import struct

D_OPS = {"lwz": 32, "lbz": 34, "lbzu": 35, "lhz": 40, "lha": 42, "sth": 44, "lwzu": 33, "stw": 36, "stwu": 37, "stb": 38, "lmw": 46, "stmw": 47,
         "lfs": 48, "stfs": 52, "lfd": 50, "stfd": 54}
IMM_OPS = {"addi": 14, "addic": 12, "addis": 15, "mulli": 7, "ori": 24, "oris": 25, "xori": 26, "xoris": 27,
           "andi.": 28, "cmpwi": 11, "cmplwi": 10}
X_OPS = {"add": 266, "subf": 40, "mullw": 235, "divwu": 459, "divw": 491, "and": 28, "andc": 60, "or": 444, "xor": 316,
         "slw": 24, "srw": 536, "lwzx": 23, "stwx": 151, "lbzx": 87, "stbx": 215, "lfsx": 535, "stfsx": 663}
FA_OPS = {"fadds": (59, 21), "fsubs": (59, 20), "fmuls": (59, 25), "fdivs": (59, 18),
          "fmadds": (59, 29), "fmsubs": (59, 28), "fadd": (63, 21), "fsub": (63, 20),
          "fmul": (63, 25), "fmadd": (63, 29)}
FX_OPS = {"fmr": 72, "fneg": 40, "fabs": 264, "frsp": 12, "fctiwz": 15}
COND = {"beq": (12, 2), "bne": (4, 2), "blt": (12, 0), "bge": (4, 0), "ble": (4, 1), "bgt": (12, 1), "bdnz": (16, 0)}
FIXED = {"blr": 0x4E800020, "bctr": 0x4E800420, "bctrl": 0x4E800421, "nop": 0x60000000}


def reg(s):
    s = s.strip().lower()
    m = re.fullmatch(r"[rf](\d+)|cr(\d)|sp", s)
    if not m:
        raise ValueError("bad register %r" % s)
    if s == "sp":
        return 1
    return int(m.group(1) if m.group(1) is not None else m.group(2))


def num(s):
    return int(s.strip(), 0)


def is_num(s):
    try:
        num(s)
        return True
    except ValueError:
        return False


def ha(v): return ((v + 0x8000) >> 16) & 0xFFFF
def lo(v): return v & 0xFFFF


class Asm:
    def __init__(self, base):
        self.base = base
        self.items = []      # (kind, data)
        self.labels = {}

    @property
    def pc(self):
        return self.base + 4 * len(self.items)

    def asm(self, text):
        for line in text.splitlines():
            line = re.split(r"[#;]", line, 1)[0].strip()
            while True:
                m = re.match(r"([A-Za-z_]\w*):\s*", line)
                if not m:
                    break
                self.labels[m.group(1)] = self.pc
                line = line[m.end():]
            if line:
                m = re.fullmatch(r"(b(?:eq|ne|lt|ge|le|gt))\.far\s+(\w+)", line)
                if m:      # long conditional branch: inverted short branch over a plain b
                    inv = {"beq": "bne", "bne": "beq", "blt": "bge", "bge": "blt", "ble": "bgt", "bgt": "ble"}
                    self.items.append("%s $+8" % inv[m.group(1)])
                    self.items.append("b %s" % m.group(2))
                else:
                    self.items.append(line)

    def addr(self, label):
        return self.labels[label]

    def target(self, s, pc=None):
        s = s.strip()
        if s.startswith("$+"):
            return pc + num(s[2:])
        if is_num(s):
            return num(s)
        if "@" in s:
            raise ValueError(s)
        return self.labels[s]

    def value(self, s):
        """immediate: number, label, label@ha / label@l (data addresses)."""
        s = s.strip()
        m = re.fullmatch(r"(\w+)@(ha|l)", s)
        if m:
            v = self.labels[m.group(1)] if not is_num(m.group(1)) else num(m.group(1))
            return ha(v) if m.group(2) == "ha" else lo(v)
        return num(s)

    def encode(self, line, pc):
        op, _, rest = line.partition(" ")
        args = [a.strip() for a in rest.split(",")] if rest.strip() else []
        if op in FIXED:
            return FIXED[op]
        if op == ".word":
            return num(args[0]) & 0xFFFFFFFF
        if op == ".float":
            return struct.unpack(">I", struct.pack(">f", float(args[0])))[0]
        if op in D_OPS:
            m = re.fullmatch(r"(.+)\((\w+)\)", args[1])
            return (D_OPS[op] << 26) | (reg(args[0]) << 21) | (reg(m.group(2)) << 16) | (self.value(m.group(1)) & 0xFFFF)
        if op in ("cmpwi", "cmplwi"):
            crf = 0
            if len(args) == 3:
                crf = reg(args.pop(0))
            return (IMM_OPS[op] << 26) | (crf << 23) | (reg(args[0]) << 16) | (self.value(args[1]) & 0xFFFF)
        if op in ("ori", "oris", "xori", "xoris", "andi."):
            return (IMM_OPS[op] << 26) | (reg(args[1]) << 21) | (reg(args[0]) << 16) | (self.value(args[2]) & 0xFFFF)
        if op in IMM_OPS:
            return (IMM_OPS[op] << 26) | (reg(args[0]) << 21) | (reg(args[1]) << 16) | (self.value(args[2]) & 0xFFFF)
        if op == "li":
            return (14 << 26) | (reg(args[0]) << 21) | (self.value(args[1]) & 0xFFFF)
        if op == "lis":
            return (15 << 26) | (reg(args[0]) << 21) | (self.value(args[1]) & 0xFFFF)
        if op in ("cmpw", "cmplw"):
            crf = 0
            if len(args) == 3:
                crf = reg(args.pop(0))
            return (31 << 26) | (crf << 23) | (reg(args[0]) << 16) | (reg(args[1]) << 11) | ((0 if op == "cmpw" else 32) << 1)
        if op in X_OPS or op.rstrip(".") in X_OPS:
            rc = op.endswith(".")
            base = op.rstrip(".")
            a, b_, c = (reg(x) for x in args)
            if base in ("and", "andc", "or", "xor", "slw", "srw"):   # rA, rS, rB
                return (31 << 26) | (b_ << 21) | (a << 16) | (c << 11) | (X_OPS[base] << 1) | rc
            return (31 << 26) | (a << 21) | (b_ << 16) | (c << 11) | (X_OPS[base] << 1) | rc
        if op in ("extsb", "extsb.", "extsh", "extsh."):   # rA, rS
            xo = 954 if op.startswith("extsb") else 922
            return (31 << 26) | (reg(args[1]) << 21) | (reg(args[0]) << 16) | (xo << 1) | op.endswith(".")
        if op in ("mr", "mr."):
            s = reg(args[1])
            return (31 << 26) | (s << 21) | (reg(args[0]) << 16) | (s << 11) | (444 << 1) | (op == "mr.")
        if op in ("rlwimi", "rlwimi."):
            ra, rs, sh, mb, me = reg(args[0]), reg(args[1]), num(args[2]), num(args[3]), num(args[4])
            return (20 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1) | (op == "rlwimi.")
        if op in ("rlwinm", "rlwinm."):
            ra, rs, sh, mb, me = reg(args[0]), reg(args[1]), num(args[2]), num(args[3]), num(args[4])
            return (21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1) | (op == "rlwinm.")
        if op in ("slwi", "srwi", "srwi.", "clrlwi", "clrlwi."):
            ra, rs, n = reg(args[0]), reg(args[1]), num(args[2])
            sh, mb, me = {"slwi": (n, 0, 31 - n), "srwi": ((32 - n) % 32, n, 31)}.get(op.rstrip("."), (0, n, 31))
            return (21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) | (mb << 6) | (me << 1) | op.endswith(".")
        if op in ("mftb", "mftbu"):                       # the time base, lower / upper word (TBR 268 / 269)
            tbr = 268 if op == "mftb" else 269
            return (31 << 26) | (reg(args[0]) << 21) | (((tbr & 31) << 5 | tbr >> 5) << 11) | (371 << 1)
        if op == "mfcr":
            return (31 << 26) | (reg(args[0]) << 21) | (19 << 1)
        if op == "mtcrf":                                # mtcrf FXM, rS
            return (31 << 26) | (reg(args[1]) << 21) | ((num(args[0]) & 0xFF) << 12) | (144 << 1)
        if op in ("mflr", "mtlr", "mtctr"):
            spr = 0x100 if op != "mtctr" else 0x120     # spr field with halves swapped (8 / 9)
            xo = 339 if op == "mflr" else 467
            return (31 << 26) | (reg(args[0]) << 21) | (spr << 11) | (xo << 1)
        if op in FA_OPS:
            prim, xo = FA_OPS[op]
            d, a = reg(args[0]), reg(args[1])
            if op in ("fmuls", "fmul"):
                return (prim << 26) | (d << 21) | (a << 16) | (reg(args[2]) << 6) | (xo << 1)
            if op.startswith("fm") and len(args) == 4:      # fmadd(s) d, a, c, b = a*c + b
                return (prim << 26) | (d << 21) | (a << 16) | (reg(args[3]) << 11) | (reg(args[2]) << 6) | (xo << 1)
            return (prim << 26) | (d << 21) | (a << 16) | (reg(args[2]) << 11) | (xo << 1)
        if op in FX_OPS:
            return (63 << 26) | (reg(args[0]) << 21) | (reg(args[1]) << 11) | (FX_OPS[op] << 1)
        if op == "frsqrte":
            return (63 << 26) | (reg(args[0]) << 21) | (reg(args[1]) << 11) | (26 << 1)
        if op == "fcmpu":
            return (63 << 26) | (reg(args[0]) << 23) | (reg(args[1]) << 16) | (reg(args[2]) << 11)
        if op in ("b", "bl"):
            off = self.target(args[0], pc) - pc
            assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, line
            return (18 << 26) | (off & 0x3FFFFFC) | (op == "bl")
        if op in COND or op.rstrip("lr") in COND and op.endswith("lr"):
            crf = 0
            if len(args) == 2:
                crf = reg(args.pop(0))
            if op.endswith("lr") and op not in COND:
                bo, bi = COND[op[:-2]]
                return (19 << 26) | (bo << 21) | ((crf * 4 + bi) << 16) | (16 << 1)
            bo, bi = COND[op]
            off = self.target(args[0], pc) - pc
            assert -0x8000 <= off < 0x8000, line
            return (16 << 26) | (bo << 21) | ((crf * 4 + bi) << 16) | (off & 0xFFFC)
        raise ValueError("unknown instruction %r" % line)

    def words(self):
        return [self.encode(line, self.base + 4 * i) & 0xFFFFFFFF for i, line in enumerate(self.items)]
