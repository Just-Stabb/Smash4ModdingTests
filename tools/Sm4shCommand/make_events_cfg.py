#!/usr/bin/env python3
"""Writes SM4SHCommand/Events.cfg from SALT's built-in command table (SALT/SALT/Scripting/AnimCMD/CMD_INFO.cs).

  python3 make_events_cfg.py

The old Events.cfg shipped with Sm4shCommand was older than SALT's table and, since it's loaded on top
of it at startup, it replaced SALT's hitbox definitions with outdated ones (Unknown fields, X/Z
swapped). Run this after updating CMD_INFO.cs. Same format as ACMD_INFO.SaveInfo (what Tools > Command
Definitions saves).
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "SALT", "SALT", "Scripting", "AnimCMD", "CMD_INFO.cs")
DST = os.path.join(HERE, "SM4SHCommand", "Events.cfg")


def table(text, name):
    i = text.index("Dictionary<uint, %s> %s" % ("int" if name == "CMD_SIZES" else "string", name))
    j = text.index("};", i)
    body = text[i:j]
    if name == "CMD_SIZES":
        return {int(k, 16): int(v) for k, v in re.findall(r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*(\d+)\s*\}", body)}
    return {int(k, 16): v for k, v in re.findall(r'\{\s*0x([0-9A-Fa-f]+)\s*,\s*"((?:[^"\\]|\\.)*)"\s*\}', body)}


def main():
    text = open(SRC, encoding="utf-8-sig").read()
    names, fmt, syn, desc = (table(text, n) for n in ("CMD_NAMES", "PARAM_FORMAT", "PARAM_SYNTAX", "CMD_DESC"))
    sizes = table(text, "CMD_SIZES")
    out = [
        "// Sm4shCommand ACMD command definitions. Read at startup on top of the built-in ones.",
        "// One block per command, blocks separated by a blank line:",
        "//   identifier (hex CRC32 of the command)",
        "//   name",
        "//   parameter types, comma separated: 0 int, 1 float, 2 decimal, 3 variable (or NONE)",
        "//   parameter names, comma separated (or NONE)",
        "//   description shown in tooltips (optional; NONE = no description)",
        "//   Param: Name = description   (optional, one line per parameter, also shown in tooltips)",
        "// Lines starting with // are comments. Tools > Command Definitions edits this file.",
    ]
    for crc, name in sorted(names.items(), key=lambda kv: kv[1].upper()):
        f = fmt.get(crc, "NONE") or "NONE"
        s = syn.get(crc, "NONE") or "NONE"
        # The size is what the parser trusts; the file stores it as (parameter count + 1). Pad a
        # definition whose list is shorter than its size (Intensity_Special_Hitbox: size 48, 46 listed).
        want = sizes.get(crc, 1) - 1
        have = 0 if f == "NONE" else len(f.split(","))
        if want > have:
            f = ",".join(([] if f == "NONE" else f.split(",")) + ["0"] * (want - have))
            s = ",".join(([] if s == "NONE" else s.split(",")) + ["Unknown"] * (want - have))
        if f == "NONE":
            s = "NONE"
        elif s == "NONE" or len(s.split(",")) != len(f.split(",")):
            n = len(f.split(","))
            have = [] if s == "NONE" else s.split(",")
            s = ",".join((have + ["Unknown"] * n)[:n])
        d = desc.get(crc, "NONE").replace('\\"', '"') or "NONE"
        out += ["", "%08X" % crc, name, f, s, d]
    open(DST, "w", newline="\r\n").write("\n".join(out) + "\n")
    print("%d commands -> %s" % (len(names), DST))


if __name__ == "__main__":
    main()
