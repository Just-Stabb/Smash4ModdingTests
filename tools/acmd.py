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

As a module: f = ACMDFile.load(path); s = f.script("specialairsstart"); edit s (a list of
Command), then f.save(path). Command(ident, params) with params as int/float.
"""
import json
import os
import struct
import sys
import zlib

END = 0x5766F889
_INFO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "acmd_info.json")))["commands"]
INFO = {int(k, 16): v for k, v in _INFO.items()}
BY_NAME = {v["name"].lower(): k for k, v in INFO.items()}


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
        syn = self.info["syntax"]
        parts = []
        for i, p in enumerate(self.params):
            k = self.kind(i)
            if k == 1:
                v = ("%g" % p) if abs(p) < 1e6 else repr(p)
            elif k == 3:
                v = "var 0x%X" % p
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
        return cls(scripts, d[4:8])

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
