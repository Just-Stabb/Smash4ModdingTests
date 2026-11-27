#!/usr/bin/env python3
"""The probe's cost against an Azahar-like stub (what the user's v1.0.1 --rsp-log showed): PacketSize=9800, qXfer
features / osdata / threads, vCont;c;C only, T00 halted at connect, empty replies for unmapped memory, code mapped
0x00100000-0x01100000, the heap 0x08000000-0x08600000 without CROs, a stack mapped only just below 0x10000000, the
modules (static.crs, enemy_fs, main_field) in the linear heap; a delay per reply (4 ms halted, 16 ms running: one
packet per run-loop pass).

  python3 tools/smashrun_trace/tests/test_probe_budget.py [DUMP_DIR]

Checks: the probe finds the modules at their bases, picks the base map and the static symbols without reading the
export tables (the dump's files: same hash blocks), within < 500 packets cold and < 50 warm (the cache), and leaves
the game running (a continue before D). Also without the game thread (no CRO pointer in any thread): the bulk scan
fallback, its packet count and time. Prints the per-step packet table.
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import world as Wd          # noqa: E402
import fake_azahar as F     # noqa: E402
import trace as cli         # noqa: E402

FAILS = []
N = [0]


def check(c, msg):
    N[0] += 1
    if not c:
        FAILS.append(msg)
        print('FAIL:', msg)


def probe_once(srv, out):
    n0 = len(srv.packets)
    t0 = time.time()
    cli.main(['probe', '--port', str(srv.port), '--out', out])
    pk = srv.packets[n0:]
    evs = [json.loads(l) for l in open(out)]
    acc = [e for e in evs if e.get('msg') == 'packet accounting']
    sess = [e for e in evs if e['t'] == 'session']
    return pk, time.time() - t0, acc[-1] if acc else {}, sess[0] if sess else {}


def table(tag, acc, pk, dt):
    print('%s: %d packets, %.1f s' % (tag, len(pk), dt))
    for r in acc.get('steps', []):
        print('   %-44s %5d packets %6.2f s  %s' % (r['step'], r['packets'], r['seconds'], r['note']))


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('S3DS_DUMP')
    if not dump or not os.path.exists(os.path.join(dump, 'static.crs')):
        print('SKIP: no dump')
        return 0
    for with_thread, layout in ((True, 'azahar'), (False, 'azahar'), (False, 'azahar_full')):
        tag = '[%s, %s] ' % ('game thread' if with_thread else 'no CRO pointer in any thread', layout)
        w = Wd.World(dump, layout=layout)
        thr = w.threads(with_cro_thread=with_thread)
        srv = F.GDBServer(w.m, F.Scenario(w.m, []), azahar=True, latency_halted=0.004, latency_running=0.016,
                          threads=thr).start()
        d = tempfile.mkdtemp()
        pk, dt, acc, sess = probe_once(srv, os.path.join(d, 'p1.jsonl'))
        table(tag + 'cold', acc, pk, dt)
        mods = {m['name']: int(m['base'], 16) for m in sess.get('modules', [])}
        check(mods.get('|static|') == w.crs_addr and mods.get('enemy_fs') == w.cro_bases['enemy_fs'][0] and
              mods.get('main_field') == w.cro_bases['main_field'][0], tag + 'modules at their bases: %s' %
              {k: hex(v) for k, v in mods.items()})
        check(sess.get('map') == 'base', tag + 'base map (by the hash block)')
        how = acc.get('how', {})
        check(how.get('|static|', '').startswith('catalogue'), tag + 'static symbols from the catalogue: %s' % how)
        if with_thread:
            check(len(pk) < 500, tag + 'cold probe under 500 packets: %d' % len(pk))
            check(how.get('modules') == 'samples', tag + 'found from the thread samples')
        else:
            check(how.get('modules') == 'scan', tag + 'found by the bulk scan')
            budget = 3500 if layout == 'azahar_full' else 500
            check(len(pk) < budget, tag + 'cold probe with the scan under %d packets: %d' % (budget, len(pk)))
        # Azahar facts used
        check(not any(p.startswith('vCont;s') for p in pk), tag + 'no vCont;s (Azahar offers c / C only)')
        check(any(p.startswith('m') and int(p.split(',')[1], 16) >= 0x4000 for p in pk), tag + 'bulk reads used')
        ci = max(i for i, p in enumerate(pk) if p in ('c', 'vCont;c'))
        check('D' in pk[ci:], tag + 'continue, then D at the end')
        check(srv.idle, tag + 'the game is left running')
        # warm: the same folder (its cache), the game still where it was
        srv.idle = False
        pk2, dt2, acc2, sess2 = probe_once(srv, os.path.join(d, 'p2.jsonl'))
        table(tag + 'warm', acc2, pk2, dt2)
        mods2 = {m['name']: int(m['base'], 16) for m in sess2.get('modules', [])}
        check(mods2 == mods, tag + 'warm: the same modules')
        check(acc2.get('how', {}).get('modules') == 'cache', tag + 'warm: from the cache')
        check(len(pk2) < 50, tag + 'warm probe under 50 packets: %d' % len(pk2))
        check(srv.idle, tag + 'warm: the game is left running')
        srv.close()
    print('probe budget: %d checks, %d failed' % (N[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
