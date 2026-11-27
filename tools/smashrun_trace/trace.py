#!/usr/bin/env python3
"""Smash Run trace: records Smash for 3DS's Smash Run in Azahar through its GDB stub. See README.md.

  python trace.py probe                      connect, list the modules / map / hooks found, change nothing, detach
  python trace.py run [options]              trace until Ctrl+C (or --duration seconds); writes a .jsonl log
  python trace.py dump {params,singletons,objects,all}   one-shot dump of what is in RAM now, then detach
  python trace.py calibrate-clock [--seconds 20]         count the frame-clock candidates' hits per second
  python trace.py resume                     unfreeze a game left paused by the stub (connect, continue, detach)

Common options: --host 127.0.0.1 --port 24689 --out FILE.jsonl
Run options:
  --mode light|full        light (default): state changes, attacks, effects, sounds, RNG, spawns / leaves, items,
                           chests, doors, stats, hazards. full: also every state update and the AI / motion /
                           kinetic / facing calls (slow: the game runs much slower)
  --kinds kuribo,heiho     only these enemy kinds (names as in docs/smash-run-enemies/); default all
  --cats ai,sound,...      exactly these categories (see README)
  --updates / --no-updates force the per-frame state update hooks on / off
  --update-every N         in full mode, log 1 update in N per enemy (default 1)
  --raw-every N            raw instance dump every N frames (default 600; 0 = first sight only)
  --hot                    also the hot hooks (GameManager::randi, ItemParamAccessor::get_param ...)
  --include TEXT / --exclude TEXT   force hooks whose name contains TEXT on / off (repeatable)
  --clock auto|none|NAME|0xADDR     the frame clock (default: the first candidate exported)
  --max-mb N               stop when the log reaches N MB (default 500)
  --duration S             stop after S seconds
  --bp z0|bkpt|auto        breakpoint method (default auto: Z0 packets, else BKPT words written and restored)
  --no-step-over           continue without stepping over the breakpoint (only if the stub does it itself)
  --map auto|update|base   which enemy_fs.cro map (default: the one whose exports match the loaded module)
  --rsp-log FILE           log every packet (debugging the connection)
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from srtrace import tracer, cro, VERSION   # noqa: E402


def build(argv=None):
    ap = argparse.ArgumentParser(description='Smash Run trace (Azahar GDB stub) v' + VERSION)
    ap.add_argument('command', nargs='?', default='run', choices=['run', 'probe', 'dump', 'calibrate-clock', 'resume'])
    ap.add_argument('what', nargs='?', default='all')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=24689)
    ap.add_argument('--out')
    ap.add_argument('--mode', choices=['light', 'full'], default='light')
    ap.add_argument('--kinds', default='all')
    ap.add_argument('--cats')
    ap.add_argument('--updates', dest='state_updates', action='store_true', default=None)
    ap.add_argument('--no-updates', dest='state_updates', action='store_false')
    ap.add_argument('--update-every', type=int, default=1)
    ap.add_argument('--raw-every', type=int, default=600)
    ap.add_argument('--hot', dest='hot_hooks', action='store_true')
    ap.add_argument('--include', action='append', default=[])
    ap.add_argument('--exclude', action='append', default=[])
    ap.add_argument('--clock', default='auto')
    ap.add_argument('--max-mb', type=int, default=500)
    ap.add_argument('--duration', type=float, default=0)
    ap.add_argument('--bp', dest='bp_mode', choices=['auto', 'z0', 'bkpt'], default='auto')
    ap.add_argument('--no-step-over', dest='step_over', action='store_false')
    ap.add_argument('--map', default='auto')
    ap.add_argument('--no-reconnect', dest='reconnect', action='store_false')
    ap.add_argument('--no-stage-dump', dest='dump_on_stage', action='store_false')
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--rsp-log')
    ap.add_argument('--title-id')
    return ap.parse_args(argv)


def probe(tr):
    t = tr.t
    print('modules:')
    for n, m in sorted(tr.mods.items(), key=lambda x: x[1].base):
        print('  %-16s 0x%08X  %s' % (n, m.base, ' '.join('%d:0x%08X+0x%X' % (ty, a, sz) for a, sz, ty in m.segments)))
    print('map: %s' % (tr.map['label'] if tr.map else 'none (enemy_fs.cro not loaded, or no map matches it)'))
    print('static symbols: %d, singletons: %s' % (len(tr.static_syms), ', '.join(sorted(tr.singletons))))
    on = sum(len(v) for v in tr.bp.values())
    print('breakpoints that would be set: %d (at %d addresses)' % (on, len(tr.bp)))
    print('clock: %s' % (tr.clock_hook.name if tr.clock_hook else 'none'))
    print('breakpoint method: %s' % ('Z0' if t.z0_ok else 'BKPT words' if t.z0_ok is False else 'untested'))


def calibrate(tr, seconds):
    """every clock candidate and the traced enemies' update slots, counted"""
    for h in tr.catalog['hooks']:
        if h['cat'] == 'clock':
            a = tr.static_syms.get(h['mangled'])
            if a:
                tr.add(tracer.Hook('clock_cand', a, h, h['name'], 'clock'))
    counts = {}
    t_end = time.time() + seconds
    st = tr.t.cont(tr.t.read_regs().get('r15'))
    while time.time() < t_end:
        if st is None:
            st = tr.t.wait(1.0)
            if st is None:
                continue
        regs = tr.t.read_regs()
        pc = regs['r15']
        for h in tr.bp.get(pc & ~1, []):
            counts[h.name] = counts.get(h.name, 0) + 1
        st = tr.t.cont(pc)
    tr.t.halt()
    print('hits in %.0f s (a per-frame function hits once a frame: compare with an enemy\'s update):' % seconds)
    for n, c in sorted(counts.items(), key=lambda x: -x[1]):
        print('  %8d  %6.1f/s  %s' % (c, c / seconds, n))
    tr.log.write({'t': 'note', 'f': 0, 'msg': 'calibrate-clock', 'counts': counts, 'seconds': seconds})


def resume(host, port):
    """connect, remove nothing, send continue and detach: unfreezes a game a stub left halted (Azahar halts the game
    while a client is connected; v1.0.0's probe detached without a continue and the game stayed frozen)"""
    from srtrace import rsp
    c = rsp.RSPClient(host, port)
    t = rsp.Target(c, log=print)
    try:
        t.attach()
        t.detach()
        print('[trace] continue sent: the game should be running again')
    finally:
        c.close()


def main(argv=None):
    a = build(argv)
    if a.command == 'resume':
        resume(a.host, a.port)
        return
    cfg = {k: v for k, v in vars(a).items() if k not in ('command', 'what', 'seconds')}
    cfg['include'] = a.include
    cfg['exclude'] = a.exclude
    if a.command != 'run' and not a.out:
        cfg['out'] = 'smashrun_%s_%s.jsonl' % (a.command.replace('-', '_'), time.strftime('%Y%m%d_%H%M%S'))
    if a.command in ('probe', 'dump'):
        cfg['dry'] = True
    if a.command == 'calibrate-clock':
        cfg['state_updates'] = True
        cfg['clock'] = 'none'
    tr = tracer.Tracer(cfg)
    if a.command == 'run':
        tr.run()
    elif a.command == 'probe':
        tr.run(one_shot=probe)
    elif a.command == 'dump':
        fn = {'params': lambda t: t.dump_params(), 'singletons': lambda t: t.dump_singletons(),
              'objects': lambda t: t.dump_objects(), 'all': lambda t: t.dump_all('requested')}[a.what]
        tr.run(one_shot=fn)
    elif a.command == 'calibrate-clock':
        tr.run(one_shot=lambda t: calibrate(t, a.seconds))


if __name__ == '__main__':
    main()
