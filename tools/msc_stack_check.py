#!/usr/bin/env python3
"""Static stack check of compiled MSC (.mscsb): for every script, the value stack depth along every
path, which must be the same wherever paths meet, never below 0, 1 at a value return and 0 at a
plain one. A function call whose value is used but never pushed (msclang's f(g(x)) bug, fixed by
tools/msclang_nested_call.patch) leaves the stack off by one and shows here.

  python3 tools/msc_stack_check.py FILE.mscsb [SOURCE.c ...]

SOURCE.c (the files compiled, in order): names the scripts by their functions.

Stack effects (p = the command's push bit): pushes +p; binary operations -2 + p; unary -1 + p;
setVar and the compound assignments -1 + p (a = b = 0); i++ / f++ 0; printf(n) -n; sys(n) -n + p; try(label) 0 and
callFunc(n) -(n + 1), then + p of its try once the call returns; callFunc2 / 3 (n) -(n + 1);
if / ifNot -1; jumps / else 0; intToFloat / floatToInt 0.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mscdec'))
from msc import MscFile  # noqa: E402

BINARY = set(range(0x0E, 0x13)) | {0x16, 0x17} | set(range(0x19, 0x1C)) | set(range(0x25, 0x2B)) | \
    set(range(0x3A, 0x3E)) | set(range(0x46, 0x4C))
UNARY = {0x13, 0x18, 0x2B, 0x3E}
PUSH = {0x0A, 0x0B, 0x0D}
ASSIGN = set(range(0x1C, 0x25)) | set(range(0x41, 0x46))
INCDEC = {0x14, 0x15, 0x3F, 0x40}
NOP = {0x00, 0x02, 0x38, 0x39}


def function_names(sources):
    src = ''.join(open(f).read() + '\n' for f in sources)
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = re.sub(r'//[^\n]*', '', src)
    return re.findall(r'^(?:int|void|float)\s+(\w+)\s*\([^;{)]*\)\s*\{', src, re.M)


def check(script):
    """[problem, ...] of one script"""
    cmds = script.cmds
    at = {c.commandPosition: i for i, c in enumerate(cmds)}
    problems = []
    seen = {}                                   # index -> (depth, tries)
    work = [(0, 0, ())]
    while work:
        i, depth, tries = work.pop()
        while i < len(cmds):
            if i in seen:
                if seen[i][0] != depth:
                    problems.append('0x%X: paths meet at depths %d and %d' % (cmds[i].commandPosition, seen[i][0], depth))
                break
            seen[i] = (depth, tries)
            c = cmds[i]
            op, p = c.command, int(c.pushBit)
            nxt = i + 1
            if op in PUSH:
                depth += p
            elif op in BINARY:
                depth += -2 + p
            elif op in UNARY:
                depth += -1 + p
            elif op in ASSIGN:
                depth += -1 + p                 # with p: its value too (a = b = 0)
            elif op in INCDEC or op in NOP:
                pass
            elif op == 0x2C:
                depth -= c.parameters[0]
            elif op == 0x2D:
                depth += -c.parameters[0] + p
            elif op == 0x2E:
                tries = tries + (p,)
            elif op == 0x2F:
                if not tries:
                    problems.append('0x%X: callFunc without a try' % c.commandPosition)
                    break
                depth += -(c.parameters[0] + 1) + tries[-1]
                tries = tries[:-1]
            elif op in (0x30, 0x31):
                depth -= c.parameters[0] + 1
            elif op in (0x34, 0x35):
                depth -= 1
                if c.parameters[0] in at:
                    work.append((at[c.parameters[0]], depth, tries))
            elif op in (0x04, 0x05, 0x36):
                if c.parameters[0] not in at:
                    problems.append('0x%X: jump out of the script' % c.commandPosition)
                    break
                nxt = at[c.parameters[0]]
            elif op == 0x06:
                if depth != 1:
                    problems.append('0x%X: return with %d on the stack (want 1)' % (c.commandPosition, depth))
                break
            elif op in (0x03, 0x07, 0x08, 0x09, 0x4D):
                if depth != 0:
                    problems.append('0x%X: return with %d on the stack (want 0)' % (c.commandPosition, depth))
                break
            elif op == 0x33:
                depth -= 1
            else:
                problems.append('0x%X: command 0x%X not modelled' % (c.commandPosition, op))
                break
            if depth < 0:
                problems.append('0x%X: stack below 0' % c.commandPosition)
                break
            i = nxt
    return problems


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    m = MscFile()
    m.readFromFile(open(sys.argv[1], 'rb'))
    scripts = sorted(m.scripts, key=lambda s: s.bounds[0])
    names = function_names(sys.argv[2:]) if len(sys.argv) > 2 else []
    if names and len(names) != len(scripts):
        print('warning: %d functions in the sources, %d scripts' % (len(names), len(scripts)))
        names = []
    bad = 0
    for k, s in enumerate(scripts):
        probs = check(s)
        if probs:
            bad += 1
            print('%s (0x%X): %s' % (names[k] if names else 'script %d' % k, s.bounds[0], '; '.join(probs[:3])))
    print('%d of %d scripts with stack problems' % (bad, len(scripts)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
