#!/usr/bin/env python3
"""Reads and edits Smash 4 ACMD files (animcmd game.bin / effect.bin / sound.bin / expression.bin).

Same binary format FITX / SALT (Sammi Husky) reads; command table from tools/acmd_info.json
(generated from SALT's CMD_INFO.cs).

Scripts are keyed by CRC32 of the lower-case animation name (e.g. "specialairsstart").

Usage:
  python3 tools/acmd.py dump game.bin NAME [NAME ...]     print scripts by animation name
  python3 tools/acmd.py dump game.bin 0xCRC                ...or by CRC
  python3 tools/acmd.py find game.bin CMDNAME              list scripts using a command (e.g. Search_Collision)
  python3 tools/acmd.py names game.bin NAMES.txt           which names in a list (one per line) have a script
  python3 tools/acmd.py vars game.bin [effect.bin ...]     the New_Var variables declared (name, slot, type, scope)

As a module: f = ACMDFile.load(path); s = f.script("specialairsstart"); edit s (a list of
Command), then f.save(path). Command(ident, params) with params as int/float.
new_var("charge", slot=0, type=1, initial=0, scope=0) makes a New_Var command (tools/acmd_ext_cave.py, exe_v40);
dump shows the variables New_Var declares in the file by name.
"""
import json
import os
import struct
import sys
import zlib

END = 0x5766F889
_INFO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "acmd_info.json")))["commands"]
INFO = {int(k, 16): v for k, v in _INFO.items()}


def _new_commands():
    """the executable's new commands (tools/acmd_ext_cave.py NEW_CMDS) that acmd_info.json doesn't list yet
    (e.g. Leave_Ground_Cancel, before Sm4shCommand's tables are regenerated)"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import acmd_ext_cave as ext
    except Exception:
        return
    for name, _label, params, _desc in ext.NEW_CMDS:
        ident = zlib.crc32(name.encode()) & 0xFFFFFFFF
        if ident not in INFO:
            INFO[ident] = {"size": 1 + len(params), "name": name, "format": [t for _n, t, _d in params],
                           "syntax": [n for n, _t, _d in params]}


_new_commands()
BY_NAME = {v["name"].lower(): k for k, v in INFO.items()}
NEW_VAR = zlib.crc32(b"New_Var") & 0xFFFFFFFF
NEW_VAR_BASE, NEW_VAR_SLOTS, NEW_VAR_NAME_WORDS = 0x0F000380, 64, 6
VAR_NAMES = {}                  # variable ID -> New_Var name, shown by Command.__str__ (ACMDFile.load fills it)


def new_var(name, slot, type=0, initial=0.0, scope=0):
    """New_Var(Name, Type 0 float / 1 int, Initial, Scope 0 object / 1 move) in slot 0-63 (ID 0x0F000380 + slot)"""
    raw = name.encode("ascii")
    assert raw and len(raw) <= 4 * NEW_VAR_NAME_WORDS and 0 <= slot < NEW_VAR_SLOTS, (name, slot)
    raw = raw.ljust(4 * NEW_VAR_NAME_WORDS, b"\0")
    words = list(struct.unpack(">%dI" % NEW_VAR_NAME_WORDS, raw))
    return Command(NEW_VAR, [NEW_VAR_BASE + slot, type, float(initial), scope] + words)


def new_var_name(c):
    """the name a New_Var command carries, or None"""
    if c.ident != NEW_VAR or len(c.params) != 4 + NEW_VAR_NAME_WORDS:
        return None
    raw = b"".join(struct.pack(">I", int(w) & 0xFFFFFFFF) for w in c.params[4:]).split(b"\0")[0]
    try:
        return raw.decode("ascii") or None
    except UnicodeDecodeError:
        return None


def crc(name):
    return zlib.crc32(name.lower().encode()) & 0xFFFFFFFF


class Command:
    def __init__(self, ident, params=None):
        self.ident = ident
        self.params = list(params or [])

    @property
    def info(self):
        return INFO.get(self.ident, {"size": 1 + len(self.params), "name": "unk_%08X" % self.ident, "format": [], "syntax": []})

    @property
    def name(self):
        return self.info["name"]

    def kind(self, i):
        fmt = self.info["format"]
        return fmt[i] if i < len(fmt) else 0

    def encode(self):
        out = struct.pack(">I", self.ident)
        for i, p in enumerate(self.params):
            if self.kind(i) == 1:
                out += struct.pack(">f", float(p))
            else:
                out += struct.pack(">I", int(p) & 0xFFFFFFFF)
        return out

    def __str__(self):
        name = new_var_name(self)
        if name:
            ident = self.params[0]
            slot = ident - NEW_VAR_BASE if NEW_VAR_BASE <= ident < NEW_VAR_BASE + NEW_VAR_SLOTS else "0x%X" % ident
            return "New_Var(Name=%s, Type=%s, Initial=%g, Scope=%s, Slot=%s)" % (
                name, {0: "float", 1: "int"}.get(self.params[1], self.params[1]), self.params[2],
                {0: "object", 1: "move"}.get(self.params[3], self.params[3]), slot)
        syn = self.info["syntax"]
        parts = []
        for i, p in enumerate(self.params):
            k = self.kind(i)
            if k == 1:
                v = ("%g" % p) if abs(p) < 1e6 else repr(p)
            elif k == 3:
                v = VAR_NAMES.get(p, "var 0x%X" % p)
            else:
                v = "0x%X" % p if p > 9 else str(p)
            parts.append("%s=%s" % (syn[i], v) if i < len(syn) else v)
        return "%s(%s)" % (self.name, ", ".join(parts))


class ACMDFile:
    def __init__(self, scripts, version_bytes=b"\0\0\0\2"):
        self.scripts = scripts  # {crc: [Command]}
        self.version_bytes = version_bytes

    @classmethod
    def load(cls, path):
        d = open(path, "rb").read()
        if d[:4] != b"ACMD":
            sys.exit("%s: not an ACMD file" % path)
        if d[4] != 0:
            sys.exit("%s: little-endian (3DS) ACMD not supported" % path)
        count, = struct.unpack(">I", d[8:12])
        table = [struct.unpack(">II", d[0x10 + i * 8:0x18 + i * 8]) for i in range(count)]
        starts = sorted(set(off for _h, off in table)) + [len(d)]
        scripts = {}
        for h, off in table:
            # a script runs to the next one's start, not its first Script_End: a Thread_Start
            # block ends with its own (Marth's SpecialHi_C2: the thread's, then the script's)
            bound = starts[starts.index(off) + 1]
            cmds = []
            a = off
            while True:
                ident, = struct.unpack(">I", d[a:a + 4])
                if ident == END:
                    cmds.append(Command(END))
                    a += 4
                    if a + 4 <= bound and struct.unpack(">I", d[a:a + 4])[0] in INFO:
                        continue
                    break
                if ident not in INFO:
                    sys.exit("unknown command 0x%08X in script 0x%08X at 0x%X" % (ident, h, a))
                c = Command(ident)
                for j in range(INFO[ident]["size"] - 1):
                    raw = d[a + 4 + j * 4:a + 8 + j * 4]
                    c.params.append(struct.unpack(">f", raw)[0] if c.kind(j) == 1 else struct.unpack(">I", raw)[0])
                cmds.append(c)
                a += INFO[ident]["size"] * 4
            scripts[h] = cmds
        f = cls(scripts, d[4:8])
        VAR_NAMES.update({c.params[0]: n for c, n in f.new_vars()})
        return f

    def new_vars(self):
        """[(New_Var command, its name)] in the file, by script"""
        return [(c, new_var_name(c)) for k in sorted(self.scripts) for c in self.scripts[k] if new_var_name(c)]

    def script(self, name_or_crc):
        h = name_or_crc if isinstance(name_or_crc, int) else crc(name_or_crc)
        return self.scripts.get(h)

    def encode(self):
        keys = sorted(self.scripts)
        body = b""
        table = b""
        base = 0x10 + 8 * len(keys)
        total = 0
        for k in keys:
            data = b"".join(c.encode() for c in self.scripts[k])
            table += struct.pack(">II", k, base + len(body))
            body += data
            total += len(self.scripts[k])
        return b"ACMD" + self.version_bytes + struct.pack(">II", len(keys), total) + table + body

    def save(self, path):
        open(path, "wb").write(self.encode())


def fmt_script(cmds, indent="  "):
    lines = []
    depth = 0
    for c in cmds:
        if c.ident == END:
            continue
        n = c.name
        if n in ("End_If", "End_Else", "End_Loop") or n.lower().startswith("end"):
            depth = max(0, depth - 1)
        lines.append(indent * (depth + 1) + str(c))
        if n in ("If_Compare", "If_Bit_Is_Set", "If", "Else", "Loop", "IF_BIT", "If_Compare2", "Bit_Is_Set") or n.lower().startswith("if") or n == "Else":
            depth += 1
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    f = ACMDFile.load(path)
    if cmd == "vars":
        seen = {}
        for p in sys.argv[2:]:
            for c, n in ACMDFile.load(p).new_vars():
                seen.setdefault((n, c.params[0]), str(c))
        for (_n, _i), text in sorted(seen.items(), key=lambda kv: kv[0][1]):
            print(text)
        return
    if cmd == "dump":
        for n in sys.argv[3:]:
            key = int(n, 16) if n.lower().startswith("0x") else crc(n)
            s = f.scripts.get(key)
            print("%s (0x%08X):" % (n, key))
            print(fmt_script(s) if s is not None else "  (no script)")
            print()
    elif cmd == "find":
        want = sys.argv[3].lower()
        for k in sorted(f.scripts):
            hits = [str(c) for c in f.scripts[k] if c.name.lower() == want]
            if hits:
                print("0x%08X: %s" % (k, "; ".join(hits)))
    elif cmd == "names":
        for line in open(sys.argv[3]):
            n = line.strip()
            if n and crc(n) in f.scripts:
                print("%s 0x%08X (%d commands)" % (n, crc(n), len(f.scripts[crc(n)]) - 1))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
