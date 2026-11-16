#!/usr/bin/env python3
"""Tests for tools/fighter_extras.py's common / fanfare: a new kind's record is added, an earlier port's own record is
never overwritten (Squirtle's KO-voice record 0x43 was replaced with Mario's by the old every-kind rewrite).

  python3 tools/fighter_extras_test.py [--rpx CROSS_F.rpx]

Without --rpx: the record merge (csb_merge / pick_kinds) on made-up records, and fanfare on a made-up fbb.
With --rpx (an executable with kind_expand's tables, e.g. exe_v46s): `common` end to end on a made-up
commonsoundtable laid out as the game's (62 vanilla records + the six earlier ports', Squirtle's his own): the
default run adds only Byleth's record (a copy of ZSS's) and keeps every other byte; --only master the same;
--replace without --only refuses; --only pzenigame --replace rewrites Squirtle's."""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fighter_extras as F  # noqa: E402

FAILS = []


def check(cond, msg):
    print(('ok    ' if cond else 'FAIL  ') + msg)
    if not cond:
        FAILS.append(msg)


def rec(nval, *pairs, name=b''):
    r = bytearray(name.ljust(16, b'\0'))
    for a, b in pairs:
        r += struct.pack('<HH', a, b)
    assert len(r) == 0x10 + 4 * nval
    return r


def unit():
    nval = 4
    base = [rec(nval, (i, 0x10), (i + 1, 0x10), (i + 2, 0x10), (0, 0x800 + i)) for i in range(62)]
    own = rec(nval, (0x36, 0x5E), (0x37, 0x5E), (0x3D, 0x5E), (0, 0x89F))       # Squirtle's own (the user's file)
    recs = base + [base[3]] * 5 + [own]                                         # 0x3E-0x42 bases' copies, 0x43 his
    zss = base[0x19]
    want = {0x3E + k: base[3] for k in range(6)}
    want[0x44] = zss
    new, done = F.csb_merge(recs, nval, want)
    check(new[0x43] == own, 'csb_merge: an earlier port\'s own record (0x43) is kept by default')
    check(new[0x44] == zss and len(new) == 0x45, 'csb_merge: the missing record (0x44) is added')
    check(new[:0x44] == recs, 'csb_merge: every record before it is unchanged')
    check(dict(done)[0x43].startswith('kept') and dict(done)[0x44] == 'added', 'csb_merge: reported %s' % done[-2:])
    new2, _d = F.csb_merge(recs, nval, {0x43: base[3]}, replace=True)
    check(new2[0x43] == base[3], 'csb_merge replace=True: rewrites the record asked for')
    # a placeholder record (the padding of an earlier run) counts as missing
    pad = recs[:0x43] + [F.csb_placeholder(nval)]
    new3, d3 = F.csb_merge(pad, nval, {0x43: base[3], 0x45: zss})
    check(new3[0x43] == base[3] and new3[0x44] == F.csb_placeholder(nval) and new3[0x45] == zss,
          'csb_merge: a placeholder is filled, a gap padded with one: %s' % d3)
    kinds = [{'name': 'pzenigame', 'cap': 'Pzenigame', 'kind': 0x46}, {'name': 'master', 'cap': 'Master', 'kind': 0x47}]
    check([r['name'] for r in F.pick_kinds(kinds, ['master'])] == ['master'] and
          [r['name'] for r in F.pick_kinds(kinds, ['0x46', 'Master'])] == ['pzenigame', 'master'] and
          F.pick_kinds(kinds, None) == kinds, 'pick_kinds: by name, Capitalised name and kind; none = all')


def fanfare(tmp):
    rows = [(0, 0, 0, 0, 0x200 + k) for k in range(0x47)]
    rows[0x46] = (0, 0, 0, 0, 0x20D)                   # an earlier port's own fanfare
    d = b'FBB\0' + struct.pack('<II', 1, len(rows)) + b''.join(struct.pack('<5I', *r) for r in rows)
    src = os.path.join(tmp, 'bgm_fighter.fbb')
    open(src, 'wb').write(d)
    out = os.path.join(tmp, 'fan')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'fighter_extras.py'), 'fanfare', src, out, '--set', '0x47=0x12'],
                       capture_output=True, text=True)
    new = open(os.path.join(out, 'sound/config/bgm_fighter.fbb'), 'rb').read()
    check(r.returncode == 0 and new[:8] == d[:8] and struct.unpack_from('<I', new, 8)[0] == 0x48 and
          new[0xC:len(d)] == d[0xC:] and struct.unpack_from('<5I', new, 0xC + 0x14 * 0x47)[4] == 0x212,
          'fanfare --set 0x47=0x12: one entry added (Marth\'s), the others byte-identical')


def common(tmp, rpx):
    import kind_expand as K
    img = K.Image(rpx)
    addr, _hi, _lo, _cmp, old = K.SOUND_NAME_TABLES['csb']
    names = [img.cstr(img.w(addr + 4 * i)) for i in range(old)]
    nval = 4
    recs = [rec(nval, (i, 0x40 + i), (i + 1, 0x40 + i), (i + 2, 0x40 + i), (0, 0x800 + i)) for i in range(old)]
    mario, zss = recs[names.index('Mario')], recs[names.index('SZerosuit')]
    own = rec(nval, (0x36, 0x5E), (0x37, 0x5E), (0x3D, 0x5E), (0, 0x89F))
    ports = [recs[names.index(n)] for n in ('Mario', 'Zelda', 'Koopa', 'Pit', 'Reflet')] + [own]
    allr = recs + ports
    d = b'CSB\0' + struct.pack('<I', 1) + struct.pack('<HH', nval, len(allr)) + b''.join(bytes(x) for x in allr)
    src = os.path.join(tmp, 'commonsoundtable.csb')
    open(src, 'wb').write(d)

    def run(*args):
        out = os.path.join(tmp, 'c%d' % len(os.listdir(tmp)))
        code = ('import sys,runpy;sys.path.insert(0,%r);import kind_expand as K;K.RPX=%r;'
                'sys.argv=["fighter_extras.py"]+sys.argv[1:];runpy.run_path(%r,run_name="__main__")'
                % (HERE, rpx, os.path.join(HERE, 'fighter_extras.py')))
        r = subprocess.run([sys.executable, '-c', code, 'common', src, out] + list(args), capture_output=True, text=True)
        p = os.path.join(out, 'sound/config/commonsoundtable.csb')
        return r, (open(p, 'rb').read() if os.path.exists(p) else None)

    size = 0x10 + 4 * nval
    i44 = K.sound_record('csb', 0x47)
    for args in ((), ('--only', 'master')):
        r, new = run(*args)
        ok = r.returncode == 0 and new is not None
        n2 = struct.unpack_from('<H', new, 10)[0] if ok else 0
        check(ok and n2 == len(allr) + 1 and new[0xC:len(d)] == d[0xC:] and new[0xC + size * i44:] == bytes(zss),
              'common %s: Byleth\'s record 0x%X added (ZSS\'s), Squirtle\'s own 0x43 and every other byte kept'
              % (' '.join(args) or '(default)', i44))
    r, new = run('--replace')
    check(r.returncode != 0 and new is None, 'common --replace without --only: refused')
    r, new = run('--only', 'pzenigame', '--replace')
    check(r.returncode == 0 and new[0xC + size * 0x43:0xC + size * 0x44] == bytes(mario) and len(new) == len(d),
          'common --only pzenigame --replace: rewrites Squirtle\'s record (asked for), nothing added')
    _ = mario


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rpx', help='an executable with kind_expand\'s tables (exe_v46s): runs common end to end')
    a = ap.parse_args()
    unit()
    with tempfile.TemporaryDirectory() as tmp:
        fanfare(tmp)
        if a.rpx:
            common(tmp, a.rpx)
        else:
            print('skip  common end to end (no --rpx)')
    print('%d failed' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
