#!/usr/bin/env python3
"""Lists which function each action/key is registered to in a decompiled fighter .c.

Action scripts are registered with sv_set_mem(0x1, key, actionId, func) (= sys_3).
Usage: python3 tools/action_table.py fighters/gekkouga/gekkouga.c [--from-main]
"""
import csv
import os
import re
import sys

KEYS = {
    0: "start (0)", 1: "start (1)", 2: "end (2)", 3: "start (3)",
    4: "frame (4)", 5: "hitlag frame (5)", 6: "end (6)", 7: "frame (7)", 8: "frame+hitlag (8)",
}
REG = re.compile(r"(?:sv_set_mem|sys_3)\(0x1, (0x[0-9a-fA-F]+|\d+), (0x[0-9a-fA-F]+|\d+), (func_\d+)\)")
FUNC = re.compile(r"^(?:void|int|float|bool) (\w+)\(")


def action_names():
    path = os.path.join(os.path.dirname(__file__), "..", "reference", "msc-note-sheet", "Actions_Fighters.csv")
    names = {}
    try:
        with open(path, newline="") as f:
            for row in csv.reader(f):
                if row and row[0].startswith("0x") and len(row) > 1:
                    names.setdefault(int(row[0], 16), row[1])
    except OSError:
        pass
    return names


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    from_main = "--from-main" in sys.argv
    names = action_names()
    table = {}
    owner = None
    seen_main = False
    with open(sys.argv[1]) as f:
        for line in f:
            m = FUNC.match(line)
            if m:
                owner = m.group(1)
                seen_main = seen_main or owner == "main"
            if from_main and not seen_main:
                continue
            for key, action, func in REG.findall(line):
                table.setdefault(int(action, 0), {})[int(key, 0)] = (func, owner)

    print("| Action | Name | Key | Script | Registered in |")
    print("|---|---|---|---|---|")
    for action in sorted(table):
        for key in sorted(table[action]):
            func, owner = table[action][key]
            print("| 0x%X | %s | %s | `%s` | `%s` |" % (
                action, names.get(action, ""), KEYS.get(key, key), func, owner))


if __name__ == "__main__":
    main()
