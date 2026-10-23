#!/usr/bin/env python3
"""Compare two .mscsb files function by function, by what each function does rather than its bytes:
the multiset of its instructions with their constants (sys calls with their ids, pushed values,
called functions by index, global / local variable numbers), ignoring jump targets and the
instruction layout. A decompile (mscdec) recompiled with msclang isn't byte-identical to the
game's compiler output, but a correct round trip does the same things in each function.

  python3 tools/msc_fingerprint.py ORIGINAL.mscsb REBUILT.mscsb [--added N] [-v]

--added N: REBUILT has N more functions at the end (added code); those aren't compared, and the
original functions may also call them (calls to them are ignored in the comparison). Prints the
functions that differ (with -v, what differs) and exits 1 if any do.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mscdec'))
import msc  # noqa: E402

JUMPS = {0x4, 0x5, 0x2e, 0x34, 0x35, 0x36}
SKIP = {0x0}                                    # nop


def load(path):
    f = msc.MscFile()
    f.readFromBytes(open(path, 'rb').read(), '<')
    return f


def tokens(f):
    starts = {s.bounds[0]: i for i, s in enumerate(f.scripts)}
    out = []
    for s in f.scripts:
        c = Counter()
        pushes = []                              # the last two values pushed
        for k, cmd in enumerate(s.cmds):
            op = cmd.command
            nxt = s.cmds[k + 1].command if k + 1 < len(s.cmds) else None
            if op in (0xe, 0x3a) and 0 in pushes[-2:]:
                c[('add0',)] += 1               # x + 0: addi or addf give the same bits
                pushes = []
                continue
            if op in (0xa, 0xd):
                pushes.append(cmd.parameters[0])
            elif op not in (0x38, 0x39):
                pushes.append(None)
            if op == 0x26:                       # notEquals = equals + not
                c[('equals',)] += 1
                c[('not',)] += 1
                continue
            if op in SKIP:
                continue
            if op == 0x35:                       # ifNot = not + if (the compilers differ)
                c[('if',)] += 1
                c[('not',)] += 1
                continue
            if op in JUMPS:
                c[(msc.COMMAND_NAMES.get(op, op),)] += 1
                continue
            if op in (0x38, 0x39):               # intToFloat / floatToInt: the stack slot depends on push order
                c[(msc.COMMAND_NAMES[op],)] += 1
                continue
            if op in (0xa, 0xd):                 # pushInt / pushShort: the same constant either way
                v = cmd.parameters[0]
                # a function's address: right before a call, or a later function's (status tables);
                # an early function's address is too often just a constant that happens to match
                ref = v in starts and v != 0 and (nxt in (0x2f, 0x30, 0x31) or starts[v] >= 60)
                c[('push', ('F%d' % starts[v]) if ref else v)] += 1
                continue
            c[(msc.COMMAND_NAMES.get(op, op),) + tuple(cmd.parameters)] += 1
        out.append(c)
    return out


def main():
    a = sys.argv[1:]
    verbose = '-v' in a
    a = [x for x in a if x != '-v']
    added = 0
    if '--added' in a:
        added = int(a[a.index('--added') + 1])
        a = a[:a.index('--added')] + a[a.index('--added') + 2:]
    ta, tb = tokens(load(a[0])), tokens(load(a[1]))
    n = len(ta)
    if len(tb) != n + added:
        print('function count: %d vs %d (+%d expected)' % (n, len(tb), added))
        sys.exit(1)
    extra = {('push', 'F%d' % i) for i in range(n, n + added)}
    fa, fb = load(a[0]), load(a[1])
    sa = {sc.bounds[0] for sc in fa.scripts}
    sb = {sc.bounds[0] for sc in fb.scripts}
    bad, refs = [], []
    for i in range(n):
        x, y = ta[i], Counter({k: v for k, v in tb[i].items() if k not in extra})
        if x != y:
            only_a, only_b = x - y, y - x
            # only pushes of values that are function addresses in their own file: a function pointer
            # passed as data (callFunc3(func_2)...) whose address moved, or a constant that matches one
            # (or a constant in one file that happens to be a function's address in the other)
            if all(k[0] == 'push' and (str(k[1]).startswith('F') or k[1] in sa or k[1] in sb) for k in only_a) and \
                    all(k[0] == 'push' and (str(k[1]).startswith('F') or k[1] in sb or k[1] in sa) for k in only_b) and \
                    sum(only_a.values()) == sum(only_b.values()):
                refs.append(i)
                continue
            bad.append(i)
            if verbose:
                print('func_%d: only original %s; only rebuilt %s' % (i, dict(only_a), dict(only_b)))
    print('%d functions, %d differ%s%s' % (n, len(bad), (': ' + ' '.join('func_%d' % i for i in bad[:40])) if bad else '',
          ' (%d more only in function addresses)' % len(refs) if refs else ''))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
