#!/usr/bin/env python3
"""Move a converted bank's start frames from eft's 0x448 to its emit start 0x44C (effect delay fix v1), in place of a
rebuild: only those fields change.

  python3 tools/effect_delay_patch.py IN.ptcl OUT.ptcl --prefix PtcMaster [--eff EF_NAME.eff ...]

eft's emitter field 0x448 is the emission count's random in percent (cross_f 0x04A4B32C), not a start frame; the delay
is 0x44C (0x04A6507C), the one-time end 0x450 on the same clock (0x04A64F70). Until effect delay fix v1,
tools/vfxb_to_ptcl.py and tools/xv2_to_ptcl.py wrote an emitter's start into 0x448, 0 into 0x44C and its duration
into 0x450: every delayed emitter started with the effect and its counts were thinned by start % (from 100 on it
emitted only its first frame's particle). This undoes exactly that on the sets named PREFIX...: an emitter with
0x448 != 0 and 0x44C == 0 gets 0x44C = that start, 0x448 = 0, and (one-time) 0x450 = start + its duration, as the
fixed converters write it. The particle buffer eft sizes from end - emit start is unchanged. Not done: eft2's own
count random (the fixed vfxb_to_ptcl's eft_rate; the old banks never had it): a rebuild brings it.

--eff: the Ultimate sources the bank was converted from: every patched emitter is checked against its source's start
(its set: prefix + the Ultimate set's name without P_, variants + their turn); a mismatch stops it (nothing written).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import ptcl  # noqa: E402

FOREVER = 0x7FFFFFFF


def patch(p, prefix):
    """the emitters of the sets named prefix... laid out the old way, patched in p's emitter bytes:
    [(set, emitter, start, old end, new end)]"""
    done = []
    for si in range(len(p.sets)):
        if not p.set_name(si).startswith(prefix):
            continue
        for x in p.sets[si]['emitters']:
            d = x['data']
            if d is not None and struct.unpack_from('>i', d, 0x448)[0] and struct.unpack_from('>i', d, 0x44C)[0]:
                # (both set: only the fixed vfxb_to_ptcl writes that, a count random on a delayed emitter; its count
                # randoms on undelayed ones would read as starts here)
                raise SystemExit('%s/%s has 0x448 and 0x44C both set: a bank converted after the fix, not patched'
                                 % (p.set_name(si), p.emitter_name(d)))
    for si in range(len(p.sets)):
        if not p.set_name(si).startswith(prefix):
            continue
        for x in p.sets[si]['emitters']:
            d = x['data']
            if d is None:
                continue
            start, st, end = struct.unpack_from('>iii', d, 0x448)
            if start == 0 or st != 0:
                continue
            new_end = end if end == FOREVER or not d[0x2FF] else start + end
            struct.pack_into('>iii', d, 0x448, 0, start, new_end)
            done.append((p.set_name(si), p.emitter_name(d), start, end, new_end))
    return done


def source_starts(effs):
    """{Ultimate set name without its P_: {emitter name: {start}}} over the .eff files (children promoted as the
    converter does)"""
    import vfxb
    import vfxb_to_ptcl as VP
    out = {}
    for path in effs:
        eff = vfxb.Eff(path)
        for si in range(len(eff.sets)):
            d = out.setdefault(eff.sets[si][2:] if eff.sets[si].startswith('P_') else eff.sets[si], {})
            for e in VP.promote_children(eff.emitters(si)):
                d.setdefault(e['name'], set()).add(max(0, int(e['emission']['start'])))
    return out


def source_of(src, set_name, prefix, emitter):
    """the starts of emitter in the source set the converted set_name came from (vfxb_to_ptcl names a set prefix + the
    Ultimate set's name without P_, a variant + its turn): the longest such name that has the emitter, or None"""
    rest = set_name[len(prefix):]
    for n in sorted((n for n in src if rest.startswith(n) and emitter in src[n]), key=len, reverse=True):
        return src[n][emitter]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--prefix', required=True, help="the converted sets' prefix (Ptc + the fighter's name)")
    ap.add_argument('--eff', nargs='*', default=[], help='the Ultimate .eff files it was converted from (a check)')
    a = ap.parse_args()
    p = ptcl.Ptcl(open(a.inp, 'rb').read())
    done = patch(p, a.prefix)
    bad, checked = [], 0
    if a.eff:
        src = source_starts(a.eff)
        unknown = []
        for sn, en, start, _e, _n in done:
            starts = source_of(src, sn, a.prefix, en)
            if starts is None:
                unknown.append('%s/%s' % (sn, en))
                continue
            checked += 1
            if start not in starts:
                bad.append('%s/%s: 0x448 %d, its source starts at %s' % (sn, en, start, sorted(starts)))
        if unknown:
            print('no source found for %d: %s' % (len(unknown), ', '.join(unknown)))
    for sn, en, start, end, new_end in done:
        print('  %-40s %-24s start %4d  end %s -> %s' % (sn, en, start, 'inf' if end == FOREVER else end,
                                                         'inf' if new_end == FOREVER else new_end))
    print('%d emitters patched (0x448 -> 0x44C)%s' % (len(done), ', %d checked against their source' % checked
                                                      if a.eff else ''))
    if bad:
        print('\n'.join(bad))
        sys.exit('not written: %d emitters don\'t match their source' % len(bad))
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    open(a.out, 'wb').write(out)


if __name__ == '__main__':
    main()
