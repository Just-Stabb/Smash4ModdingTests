#!/usr/bin/env python3
"""Effect delay fix v1: the converters' eft timing (emit start 0x44C, count random 0x448) and port_check E16.

  python3 -I tools/effect_delay_test.py [--eff EFF --base BASE_DIR --ids IDS_JSON EFFECT ...]

eft's emitter field 0x448 is the emission count's random in percent (each emission adds rate x (1 - U x it / 100) to
the count: cross_f 0x04A4B32C), not a start frame; the delay is 0x44C (the first emission at that frame of the
emitter's clock, 0x04A6507C), the one-time end frame 0x450 on the same clock (0x04A64F70). Greninja skeleton v1.3
found it in game (flipbook runs placed by their start in 0x448 all spawned at frame 0). vfxb_to_ptcl.py and
xv2_to_ptcl.py wrote their start frames into 0x448 until this fix: every delayed emitter started with the effect, its
counts thinned by its start %.

Without arguments: the converters' timing writers on a bare emitter, eft2's count random against eft's,
port_check's E16 on banks laid out both ways, and tools/effect_delay_patch.py (an old bank's layout to the fixed one).
With --eff / --base / --ids and Ultimate effect names (e.g. Byleth's ef_master.eff, szerosuit's vanilla effect folder,
fighters/master/master_effects.json, master_smash_hi): those effects converted by tools/vfxb_to_ptcl.py into a
temporary folder (the ids file copied there: the converter rewrites it), every converted emitter checked against its
source's start, duration and count random.
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import numpy as np  # noqa: E402
import ptcl  # noqa: E402
import effect_delay_patch as EDP  # noqa: E402
import port_check as PC  # noqa: E402
import vfxb_to_ptcl as VP  # noqa: E402
import xv2_to_ptcl as XP  # noqa: E402

FOREVER = 0x7FFFFFFF
fails = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else '\n     got  %r\n     want %r' % (got, want)))
    if not ok:
        fails.append(what)


P = ptcl.Ptcl.__new__(ptcl.Ptcl)        # (field / set_field only read the emitter's bytes)


def raw(em):
    """(0x448, 0x44C, 0x450, one-time byte 0x2FF) as the game reads them"""
    return struct.unpack_from('>iii', em, 0x448) + (em[0x2FF],)


def ems(start=0, duration=1, one=1, interval=0, interval_random=0, rate=1.0, rate_random=0):
    return {'start': start, 'duration': duration, 'one_time': one, 'interval': interval,
            'interval_random': interval_random, 'rate': rate, 'rate_random': rate_random}


def converters():
    check('ptcl.py: 0x448 is emit_rate_random (start_frame its old alias), 0x44C emit_start, 0x450 end_frame',
          (ptcl.FIELD['emit_rate_random'][0], ptcl.FIELD['start_frame'][0], ptcl.FIELD['emit_start'][0],
           ptcl.FIELD['end_frame'][0]), (0x448, 0x448, 0x44C, 0x450))
    # vfxb_to_ptcl: Ultimate (eft2) emission
    em = bytearray(0x8BC)
    struct.pack_into('>i', em, 0x448, 77)            # (a template's leftover: overwritten)
    VP.write_timing(P, em, ems(start=12, duration=5, interval=2), True, 1.0)
    check('vfxb: a delayed one-time emitter (start 12, 5 frames): 0x44C 12, 0x448 0, end 17 on the same clock',
          raw(em), (0, 12, 17, 1))
    VP.write_timing(P, em, ems(start=7, one=0, interval=3), False, 2.0)
    check('vfxb: a delayed looping emitter (start 7): 0x44C 7, 0x448 0, end 0x7FFFFFFF, one-time 0', raw(em),
          (0, 7, FOREVER, 0))
    old = bytearray(0x8BC)
    struct.pack_into('>iii', old, 0x448, 0, 0, 5)    # the layout the old converter gave an undelayed emitter
    old[0x2FF] = 1
    VP.write_timing(P, em, ems(start=0, duration=5), True, 1.0)
    check('vfxb: an undelayed emitter keeps the old layout (0x448 0, 0x44C 0, end = its duration)', raw(em), raw(old))
    VP.write_timing(P, em, ems(start=3, duration=4, interval=1), True, 1.0)
    check('vfxb: the particle buffer eft sizes from end - emit start is the old one ((4 / 2 + 1) x rate)',
          XP.buffer_count(P, em), 3)
    VP.write_timing(P, em, ems(start=4, duration=10, rate=0.5, rate_random=50), True, 0.5)
    check('vfxb: eft2\'s count random 50 % (rate 0.5 .. 0.75 an emission) -> eft rate 0.75, 0x448 33 (0.75 x '
          '(1 - U x 0.33)), the start still in 0x44C', (P.field(em, 'emit_rate'),) + raw(em), (0.75, 33, 4, 14, 1))
    check('vfxb: eft_rate without a count random: the rate as it is, 0x448 0', VP.eft_rate(2.5, 0.0), (2.5, 0))
    # the two games' counts an emission: eft2 rate + rate x r x U (main.bin 0x8D408), eft rate' (1 - U x r' / 100)
    u = (np.arange(10000) + 0.5) / 10000
    for rate, pct in ((1.0, 50), (0.5, 60), (3.0, 20), (2.0, 10)):
        r2 = rate + rate * pct / 100 * u
        r1, p1 = VP.eft_rate(rate, pct / 100)
        r4 = r1 * (1 - u * p1 / 100)
        check('vfxb: count random %d %% at rate %g: eft\'s range and mean as eft2\'s (within 1 %%: 0x448 is whole)'
              % (pct, rate), [abs(a - b) / rate < 0.01 for a, b in ((r2.min(), r4.min()), (r2.max(), r4.max()),
                                                                     (r2.mean(), r4.mean()))], [True] * 3)
    # xv2_to_ptcl: Xenoverse 2 spawn schedules
    em = bytearray(0x8BC)
    struct.pack_into('>i', em, 0x448, 9)
    start, end, interval, rate = XP.schedule([10, 10, 14, 14, 18, 18], False)
    XP.write_timing(P, em, start, end, interval, rate)
    check('xv2: spawns at 10, 14, 18 (two each): 0x44C 10, 0x448 0, end 19, interval 3, rate 2',
          raw(em) + (P.field(em, 'emit_interval'), P.field(em, 'emit_rate')), (0, 10, 19, 1, 3, 2.0))
    XP.write_timing(P, em, 6, FOREVER, 0, 1.0)
    check('xv2: a looping node from frame 6: 0x44C 6, end 0x7FFFFFFF, one-time 0', raw(em), (0, 6, FOREVER, 0))
    XP.write_timing(P, em, *XP.schedule([0, 2, 4], False))
    check('xv2: an undelayed node as before (0x44C 0, end 5)', raw(em), (0, 0, 5, 1))


class Bank:
    """a stand-in Ptcl: sets [(name, [(emitter name, 0x448, 0x44C[, 0x450, one-time])])]"""

    def __init__(self, sets):
        self.names = [n for n, _ in sets]
        self.sets = []
        for _n, ems_ in sets:
            out = []
            for en, r, st, *more in ems_:
                d = bytearray(0x8BC)
                struct.pack_into('>ii', d, 0x448, r, st)
                if more:
                    struct.pack_into('>i', d, 0x450, more[0])
                    d[0x2FF] = more[1]
                out.append({'data': d, 'name': en})
            self.sets.append({'emitters': out})

    def set_name(self, i):
        return self.names[i]

    def emitter_name(self, d):
        return next(e['name'] for s in self.sets for e in s['emitters'] if e['data'] is d)

    field = ptcl.Ptcl.field


class Rep:
    def __init__(self):
        self.items = []

    def add(self, level, code, msg):
        self.items.append((level, code))


class Inst:
    def glob(self, pat):
        return ['fighter/master/effect/master/master.010d0000.ptcl']

    def get(self, path):
        return b''


def e16(bank):
    real = ptcl.Ptcl
    ptcl.Ptcl = lambda data: bank
    try:
        rep = Rep()
        PC.check_emit_start(Inst(), 'master', rep)
    finally:
        ptcl.Ptcl = real
    return rep.items


def port_check():
    old = Bank([('PtcMasterSmashHi', [('wind_start2', 4, 0), ('wind1_br', 4, 0), ('line', 0, 0)]),
                ('PtcSzerosuitAttack', [('vanilla', 50, 3)])])
    check('E16: a bank built before the fix (start frames in 0x448, no converted emit start): ERROR', e16(old),
          [('ERROR', 'E16 emit-start')])
    new = Bank([('PtcMasterSmashHi', [('wind_start2', 0, 4), ('wind1_br', 33, 4), ('line', 33, 0)]),
                ('PtcSzerosuitAttack', [('vanilla', 50, 0)])])
    check('E16: a fixed bank (delays in 0x44C; eft2\'s count random on an undelayed emitter; the base\'s own sets '
          'not looked at): nothing', e16(new), [])
    over = Bank([('PtcMasterSmashHi', [('a', 0, 4), ('b', 120, 0)])])
    check('E16: a count random of 100 % or more (no emission after the first frame\'s): ERROR', e16(over),
          [('ERROR', 'E16 emit-start')])
    found = PC.emit_start_findings(old, 'PtcMaster')
    check('E16 findings: (over, no start, started) of the old bank',
          [len(x) if isinstance(x, list) else x for x in found], [0, 2, 0])


def patch_tool():
    """tools/effect_delay_patch.py: an old bank's layout (start in 0x448, 0 in 0x44C, the duration in 0x450) to the
    fixed converters' layout"""
    bank = Bank([('PtcMasterA', [('delayed', 4, 0, 10, 1), ('looping', 7, 0, FOREVER, 0), ('undelayed', 0, 0, 5, 1)]),
                 ('PtcSzerosuitB', [('vanilla', 50, 0, 3, 1)])])
    done = EDP.patch(bank, 'PtcMaster')
    got = [raw(e['data']) for s_ in bank.sets for e in s_['emitters']]
    fixed = bytearray(0x8BC)
    VP.write_timing(P, fixed, ems(start=4, duration=10), True, 1.0)
    check('patch: start 4 / 10 frames -> (0, 4, 14), the looping one -> (0, 7, inf), the undelayed one and the base\'s '
          'vanilla set (a real count random 50) untouched; the patched one as the fixed converter writes it',
          (got, [d[:3] for d in done], raw(fixed)),
          ([(0, 4, 14, 1), (0, 7, FOREVER, 0), (0, 0, 5, 1), (50, 0, 3, 1)],
           [('PtcMasterA', 'delayed', 4), ('PtcMasterA', 'looping', 7)], (0, 4, 14, 1)))
    check('patch: run again, nothing left to patch', EDP.patch(bank, 'PtcMaster'), [])
    try:
        EDP.patch(Bank([('PtcMasterA', [('both', 33, 4, 14, 1)])]), 'PtcMaster')
        refused = False
    except SystemExit:
        refused = True
    check('patch: a bank converted after the fix (0x448 and 0x44C both set on an emitter) is refused', refused, True)


def real_conversion(a):
    import vfxb
    eff = vfxb.Eff(a.eff)
    want = {}
    for name in a.effects:
        for e in VP.promote_children(eff.emitters(eff.effects[name.lower()])):
            s = e['emission']
            one = bool(s['one_time'])
            dur = int(s['duration'])
            if e['particle']['infinite_life'] and not one:
                one, dur = True, 1
            start = max(0, int(s['start']))
            rr = 0 if s['emit_dist_enabled'] else VP.eft_rate(1.0, max(0, int(s['rate_random'])) / 100)[1]
            key = (start, start + max(1, dur) if one else FOREVER, rr)
            want.setdefault(e['name'], set()).add(key)
    tmp = tempfile.mkdtemp(prefix='effect_delay_')
    try:
        ids = os.path.join(tmp, 'ids.json')
        shutil.copy(a.ids, ids)
        out = os.path.join(tmp, 'out')
        os.makedirs(out)
        subprocess.run([sys.executable, os.path.join(HERE, 'vfxb_to_ptcl.py'), a.eff, a.base, out, a.kind, ids]
                       + a.effects, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        path = next(os.path.join(out, f) for f in os.listdir(out) if f.endswith('.ptcl'))
        p = ptcl.Ptcl(open(path, 'rb').read())
        bad, seen, delayed = [], 0, 0
        for si in range(len(p.sets)):
            if not p.set_name(si).startswith(a.prefix):
                continue                    # (the base's own sets)
            for x in p.sets[si]['emitters']:
                d = x['data']
                n = d is not None and p.emitter_name(d)
                if not n or n not in want or len(want[n]) != 1:
                    continue
                seen += 1
                got = (p.field(d, 'emit_start'), p.field(d, 'end_frame'), p.field(d, 'emit_rate_random'))
                exp = next(iter(want[n]))
                delayed += exp[0] > 0
                if got != exp:
                    bad.append('%s/%s %r != %r' % (p.set_name(si), n, got, exp))
        print('     %d converted emitters matched to their source (%d delayed)' % (seen, delayed))
        check('real conversion (%s): every emitter\'s 0x44C its start, 0x450 start + duration, 0x448 its count '
              'random (0 without)' % ', '.join(a.effects), (bad, seen > 0), ([], True))
        over, no_start, started = PC.emit_start_findings(p, a.prefix)
        check('real conversion: port_check E16 finds nothing to flag', (over, bool(no_start) and not started),
              ([], False))
    finally:
        shutil.rmtree(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('effects', nargs='*')
    ap.add_argument('--eff')
    ap.add_argument('--base')
    ap.add_argument('--ids')
    ap.add_argument('--kind', default='0x47')
    ap.add_argument('--prefix', default='PtcEdge', help="the converted sets' prefix (vfxb_to_ptcl.py's --prefix)")
    a = ap.parse_args()
    converters()
    port_check()
    patch_tool()
    if a.eff and a.base and a.ids and a.effects:
        real_conversion(a)
    print('%d failed' % len(fails) if fails else 'all passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
