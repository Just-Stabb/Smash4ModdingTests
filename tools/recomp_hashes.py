#!/usr/bin/env python3
"""Which functions of an ssbu-recomp fighter dump read which params (hash40 names), and the calls
around them.

  python3 tools/recomp_hashes.py DUMP_DIR VL_PRC LABELS_CSV [--names a,b,...] [--calls FUNC]

DUMP_DIR: ssbu-recomp's output for one fighter (lua2cpp_<name>/: c_*.c, imports.c), the user's own
dump run through OpenSmash-Ultimate's ssbu-recomp. It is the NRO translated instruction by
instruction (no names, no data section), so a hash40 (param_special_s, speed_x...) is a movz / movk
run into one register: rebuilt here per function and matched against every label of the fighter's
vl.prc (and --names). Prints, per function, the hashes it builds in order: enough to tell which
status reads which param (e.g. Squirtle's Withdraw: param_special_s speed_x / accel_x / hit_speed_y).
--calls FUNC: that function's lines with the rebuilt constants and the imported calls named.
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prc  # noqa: E402
import ultimate_acmd as U  # noqa: E402

FUNC = re.compile(r'void (f_[0-9a-f]+)\(Ctx \*c\)')
MOVZ = re.compile(r'c->x\[(\d+)\] = \(uint64_t\)\((0x[0-9a-f]+)ULL\);')
MOVK = re.compile(r'c->x\[(\d+)\] = \(uint64_t\)\(\(c->x\[(\d+)\] & ~(0x[0-9a-f]+)ULL\) \| (0x[0-9a-f]+)ULL\);')


def label_names(vl_prc, labels):
    names = set()

    def walk(v):
        if isinstance(v, dict):
            for k, x in v.items():
                names.add(str(k))
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(prc.Prc(open(vl_prc, 'rb').read(), prc.load_labels(labels)).root)
    return names


def scan(dump):
    """{function: [(line, value)]} for every register value a movz / movk run builds"""
    out = {}
    for f in sorted(glob.glob(os.path.join(dump, 'c_*.c'))):
        cur, regs = None, {}
        for line in open(f, errors='replace'):
            m = FUNC.match(line)
            if m:
                cur, regs = m.group(1), {}
                out[cur] = []
                continue
            m = MOVZ.search(line)
            if m:
                regs[m.group(1)] = int(m.group(2), 16)
                continue
            m = MOVK.search(line)
            if m and m.group(1) == m.group(2) and m.group(1) in regs:
                v = (regs[m.group(1)] & ~int(m.group(3), 16)) | int(m.group(4), 16)
                regs[m.group(1)] = v
                if cur and v >> 32:
                    out[cur].append((line.strip(), v))
    return out


def imports(dump):
    names = []
    for line in open(os.path.join(dump, 'imports.c'), errors='replace'):
        m = re.match(r'\s*\{ "([^"]*)",', line)
        if m:
            names.append(m.group(1))
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dump')
    ap.add_argument('vl_prc')
    ap.add_argument('labels')
    ap.add_argument('--names', default='')
    ap.add_argument('--calls')
    a = ap.parse_args()
    names = label_names(a.vl_prc, a.labels) | {n for n in a.names.split(',') if n}
    for line in open(a.labels, errors='replace'):          # every known label (status / kinetic names too)
        p = line.strip().split(',', 1)
        if len(p) == 2:
            names.add(p[1])
    by_hash = {U.hash40(n): n for n in names if n}
    found = scan(a.dump)
    if a.calls:
        imp = imports(a.dump)
        for f in sorted(glob.glob(os.path.join(a.dump, 'c_*.c'))):
            text = open(f, errors='replace').read()
            i = text.find('void %s(Ctx *c)' % a.calls)
            if i < 0:
                continue
            body = text[i:text.find('\n}\n', i)]
            for line in body.splitlines():
                m = re.search(r'nro_import\(c, &\w+, (\d+)\)', line)
                note = imp[int(m.group(1))] if m and int(m.group(1)) < len(imp) else ''
                for h in re.findall(r'0x([0-9a-f]+)ULL', line):
                    if int(h, 16) in by_hash:
                        note += ' ' + by_hash[int(h, 16)]
                print(line + ('    // ' + note if note else ''))
            for _l, v in found.get(a.calls, []):
                if v in by_hash:
                    print('// builds %s' % by_hash[v])
        return
    for fn, vals in found.items():
        hit = [by_hash[v] for _l, v in vals if v in by_hash]
        if hit:
            print('%s: %s' % (fn, ', '.join(hit)))


if __name__ == '__main__':
    main()
