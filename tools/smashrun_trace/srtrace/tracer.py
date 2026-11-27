"""The Smash Run tracer: breakpoints on the hand-read enemy functions (enemy_fs.cro) and the framework (code.bin, by
name through static.crs), each stop decoded into one JSON line.

Event lines (`t` = type; every event has `f`, the frame from the clock, and `w`, seconds since the start):
  session    header: toolkit version, title id, modules (name, base, segments), the map used, the config
  module     a module found / gone (name, base)
  hook       a hook installed / refused / disabled (and why)
  clock      every `clock_log_every` frames: the frame counter's progress
  spawn      a behaviour created (kind, variation, instance, accessor) -> later events carry `inst`
  raw        an instance's / object's raw bytes (hex) for finding unknown fields
  state      a state function hit: kind, inst, state id, role (enter / update / exit), the instance snapshot
             (pos, lr, move, fields, kinetic energy words)
  slot       a vtable slot hit (tread, initialize, start, death_state, ...) with the snapshot
  call       a framework call: hook name, category, decoded args, the caller (module + file offset), the owner
             (instance when `this` or a module pointer is an enemy's), `id` for the matching `ret`
  ret        a captured return value (r0 and s0) for the call `id`
  dump       a one-shot dump (params, singletons, gimmick objects, ...)
  note       anything else (reconnects, caps, errors)
"""
import json
import os
import struct
import sys
import time
import socket

from . import VERSION, TITLE_ID
from . import rsp, cro, abi, locate

HERE = os.path.dirname(os.path.abspath(__file__))

MODULE_OFFS = {0x3040: 'Ai', 0x3048: 'Attack', 0x3054: 'Damage', 0x3058: 'Effect', 0x305C: 'Ground',
               0x3068: 'Kinetic', 0x306C: 'BehaviorModule', 0x3070: 'Motion', 0x3098: 'Model', 0x309C: 'Posture',
               0x30B0: 'KineticEnergy'}
ATTACK_NAMES = ['state', 'id', 'part', 'node', 'power', 'angle', 'kbg', 'fkb', 'bkb', 'size', 'x', 'y', 'z']
ATTACK_FLOATS = {10, 11, 12, 14, 15, 16}

LIGHT_CATS = {'clock', 'state', 'attack', 'effect', 'sound', 'rng', 'spawn', 'leave', 'damage', 'item', 'chest',
              'door', 'stat', 'stage', 'result', 'article', 'param', 'hazard'}
FULL_CATS = LIGHT_CATS | {'ai', 'motion', 'kinetic', 'facing'}

DEFAULTS = {
    'host': '127.0.0.1', 'port': 24689, 'out': None, 'mode': 'light', 'kinds': 'all', 'cats': None,
    'state_updates': None,          # None = by mode (full: every update; light: none)
    'update_every': 1,              # log one update event in N per instance (full mode)
    'raw_every': 600,               # raw instance dump every N frames (0: first sight only)
    'raw_size': 0x200,
    'max_mb': 500, 'hot_limit': 3000, 'hot_window': 5.0,
    'bp_mode': 'auto', 'step_over': True,
    'clock': 'auto', 'clock_log_every': 600,
    'rescan_every': 10.0, 'reconnect': True, 'duration': 0,
    'maps': None, 'map': 'auto', 'regions': None,
    'dump_on_stage': True, 'dump_delay': 120,
    'hot_hooks': False,             # allow the 'hot' catalogue hooks (randi, ItemParam get_param ...)
    'return_values': True,
    'include': [], 'exclude': [],   # extra hook name substrings to force on / off
    'rsp_log': None,
    'dry': False,                   # probe: resolve everything, plant nothing
    'eager_kinds': False,           # all kinds' state hooks at once (default: a kind's when its first one spawns)
    'samples': 3,                   # thread / stack samples looking for a CRO before the bulk scan
}


def f32(v):
    return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0]


def rf(x):
    return abi.rnd(x)


class Log:
    def __init__(s, path, max_mb):
        s.path = path
        s.f = open(path, 'a', encoding='utf-8')
        s.bytes = os.path.getsize(path) if os.path.exists(path) else 0
        s.cap = max_mb * 1024 * 1024 if max_mb else 0
        s.capped = False
        s.t0 = time.time()
        s.count = 0

    def write(s, ev):
        if s.capped:
            return
        ev.setdefault('w', round(time.time() - s.t0, 3))
        line = json.dumps(ev, separators=(',', ':')) + '\n'
        s.f.write(line)
        s.bytes += len(line)
        s.count += 1
        if s.count % 200 == 0:
            s.f.flush()
        if s.cap and s.bytes > s.cap:
            s.f.write(json.dumps({'t': 'note', 'msg': 'log size cap reached (%d MB): stopping' % (s.cap >> 20)}) + '\n')
            s.capped = True
            s.f.flush()

    def close(s):
        s.f.flush()
        s.f.close()


class Hook:
    """one breakpoint role: kind 'func' (catalogue), 'state', 'slot', 'create', 'clock', 'ret', 'cro'"""
    __slots__ = ('kind', 'data', 'addr', 'thumb', 'name', 'cat', 'plan', 'want_ret', 'count', 'window', 'wstart')

    def __init__(s, kind, addr, data=None, name=None, cat=None, plan=None, want_ret=False, thumb=False):
        s.kind, s.addr, s.data, s.name, s.cat, s.plan, s.want_ret, s.thumb = kind, addr, data, name, cat, plan, \
            want_ret, thumb
        s.count = 0
        s.window = 0
        s.wstart = time.time()


class Tracer:
    def __init__(s, cfg, log_print=print):
        s.cfg = dict(DEFAULTS)
        s.cfg.update({k: v for k, v in cfg.items() if v is not None})
        s.say = log_print
        s.catalog = json.load(open(os.path.join(HERE, 'catalog.json')))
        s.maps = s._load_maps()
        s.t = None
        s.log = None
        s.frame = 0
        s.clock_hook = None
        s.mods = {}
        s.map = None
        s.map_kinds_by_index = {}
        s.bp = {}                # addr -> [Hook]
        s.instances = {}         # inst ptr -> info
        s.modptr = {}            # module object ptr -> (inst, module name)
        s.pending = {}           # return addr -> [(sp, call id, hook)]
        s.call_id = 0
        s.last_ctx = None
        s.next_rescan = 0
        s.dump_at = None
        s.stop_flag = False
        s.cats = set(s.cfg['cats'].split(',')) if s.cfg['cats'] else \
            (FULL_CATS if s.cfg['mode'] == 'full' else LIGHT_CATS)
        s.kinds = None if s.cfg['kinds'] in ('all', None) else set(s.cfg['kinds'].split(','))
        s.state_updates = s.cfg['state_updates'] if s.cfg['state_updates'] is not None else s.cfg['mode'] == 'full'
        s.static_syms = {}
        s.singletons = {}

    # ------------------------------------------------------------------------------------------------ setup
    def _load_maps(s):
        d = s.cfg['maps'] or os.path.join(HERE, 'maps')
        out = {}
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.json'):
                m = json.load(open(os.path.join(d, fn)))
                out[m['label']] = m
        return out

    def open(s):
        out = s.cfg['out'] or 'smashrun_trace_%s.jsonl' % time.strftime('%Y%m%d_%H%M%S')
        s.cfg['out'] = out
        s.log = Log(out, s.cfg['max_mb'])
        trace = None
        if s.cfg['rsp_log']:
            fh = open(s.cfg['rsp_log'], 'a')
            trace = lambda d, b: fh.write('%s %r\n' % (d, b))
        s.client = rsp.RSPClient(s.cfg['host'], s.cfg['port'], trace=trace)
        s.t = rsp.Target(s.client, log=s.note, bp_mode=s.cfg['bp_mode'], step_over=s.cfg['step_over'])

    def note(s, msg, **kw):
        s.say(msg)
        if s.log:
            ev = {'t': 'note', 'f': s.frame, 'msg': msg}
            ev.update(kw)
            s.log.write(ev)

    def connect(s):
        feats, stop = s.t.attach()
        s.note('[trace] connected to %s:%d, stub features: %s' % (s.cfg['host'], s.cfg['port'],
                                                                   ', '.join(sorted(str(k) for k in feats))))
        if stop.exited:
            raise rsp.RSPError('the stub reports no running game (%s)' % stop.raw)
        cache = os.path.join(os.path.dirname(os.path.abspath(s.cfg['out'])), locate.CACHE_NAME)
        s.loc = locate.Locator(s.t, s.say, cache, s.catalog, s.maps, s.cfg['regions'])
        s.loc.stop_thread = stop.thread
        # Azahar: '?' -> T00 at connect, the game halted (user's --rsp-log); signal 0 counts as a stop too
        s.loc.measure(stop_state_running=False)
        s.loc.steps.start('read size')
        n = s.t.find_max_read()
        s.loc.steps.end('up to 0x%X bytes a packet' % n)
        s.log.write({'t': 'note', 'f': 0, 'msg': 'latency', 'latency': s.loc.latency, 'max_read': n})
        return feats

    def find_modules(s):
        s.mods = s.loc.find(s.cfg['samples'])
        s.loc.remember(s.mods)
        if s.loc.osdata_text is not None:
            s.log.write({'t': 'note', 'f': 0, 'msg': 'qXfer:osdata', 'osdata': s.loc.osdata_text})
        return s.mods

    def module_addrs(s, m, hooks):
        """{mangled: run-time address} of the wanted exports of module m: the catalogue's own offsets when m is the
        file the catalogue was built from (same hash block), else the export table (cached per hash)"""
        src = s.catalog.get('source', {})
        label = src.get('label', 'base')
        names = [h['mangled'] for h in hooks]
        same = (getattr(m, 'hash80', None) and (m.hash80 == src.get('static_crs_hash80') if m.name == '|static|'
                                                else m.hash80 == (src.get('module_hash80') or {}).get(m.name)))
        out = {}
        if same:
            s.loc.how[m.name] = 'catalogue (same %s)' % ('static.crs' if m.name == '|static|' else m.name)
            for h in hooks:
                e = h.get('expected', {}).get(label)
                if not e:
                    continue
                out[h['mangled']] = int(e, 16) if e.startswith('0x') else m.base + int(e.split('+')[1], 16)
            return out
        tags = s.loc.export_tags(m, names, 'static' if m.name == '|static|' else 'cro')
        for n, tg in tags.items():
            if tg and tg[0] < len(m.segments):
                out[n] = m.segments[tg[0]][0] + tg[1]
        return out

    def static_module(s):
        for n, m in s.mods.items():
            if n == '|static|' or n == 'static' or (m.segments and m.segments[0][0] == 0x100000):
                return m
        return None

    def choose_map(s):
        ef = s.mods.get('enemy_fs')
        if not ef:
            return None
        for label, mp in s.maps.items():
            if mp.get('hash80') and mp['hash80'] == getattr(ef, 'hash80', None) and s.cfg['map'] in ('auto', label):
                s.say('[trace] map %s: the loaded enemy_fs.cro is the file the map was read from' % label)
                s.map = mp
                s.map_kinds_by_index = {v['index']: k for k, v in mp['kinds'].items()}
                return mp
        names = sorted(set(v['create_mangled'] for mp in s.maps.values() for v in mp['kinds'].values()))
        ex = s.loc.export_tags(ef, names, 'cro')
        best, score = None, -1
        for label, mp in s.maps.items():
            if s.cfg['map'] not in ('auto', label):
                continue
            segs = mp.get('file_segments') or [[0x180, 0, 0]]
            ok = bad = 0
            for k, v in mp['kinds'].items():
                tag = ex.get(v['create_mangled'])
                if not tag:
                    continue
                fo = (segs[tag[0]][0] if tag[0] < len(segs) else 0x180) + tag[1]
                if fo == v['create']:
                    ok += 1
                else:
                    bad += 1
            s.say('[trace] map %s: %d kinds match the loaded enemy_fs.cro, %d differ' % (label, ok, bad))
            if ok > score and bad == 0 or (ok > score and s.cfg['map'] == label):
                best, score = mp, ok
        s.map = best
        if best:
            s.map_kinds_by_index = {v['index']: k for k, v in best['kinds'].items()}
        return best

    def header(s):
        st = s.static_module()
        crs_id = None
        if st:
            h = s.t.try_read(st.base, 0x20)
            crs_id = h.hex() if h else None
        s.log.write({'t': 'session', 'f': 0, 'toolkit': VERSION, 'title_id': s.cfg.get('title_id') or TITLE_ID,
                     'crs_hash': crs_id, 'map': s.map['label'] if s.map else None,
                     'modules': [{'name': m.name, 'base': '0x%08X' % m.base, 'segments':
                                  [['0x%08X' % a, '0x%X' % n, t] for a, n, t in m.segments]} for m in s.mods.values()],
                     'config': {k: v for k, v in s.cfg.items() if k != 'regions'}, 'time': time.ctime()})

    # ------------------------------------------------------------------------------------------------ hooks
    def resolve_static(s):
        st = s.static_module()
        s.static_syms = {}
        if st:
            want = [h for h in s.catalog['hooks'] if h['module'] == 'static'] + \
                list(s.catalog.get('singletons', {}).values())
            s.static_syms = s.module_addrs(st, want)
        for nm, sg in s.catalog.get('singletons', {}).items():
            a = s.static_syms.get(sg['mangled'])
            if a:
                s.singletons[nm] = a
        return st

    def add(s, h):
        lst = s.bp.setdefault(h.addr & ~1, [])
        if not lst and not s.cfg.get('dry'):
            if not s.t.add_bp(h.addr, h.thumb):
                s.bp.pop(h.addr & ~1, None)
                return False
        lst.append(h)
        return True

    def drop(s, h):
        lst = s.bp.get(h.addr & ~1, [])
        if h in lst:
            lst.remove(h)
        if not lst and (h.addr & ~1) in s.bp:
            del s.bp[h.addr & ~1]
            s.t.remove_bp(h.addr)

    def want_hook(s, h):
        nm = h['name']
        if any(x in nm for x in s.cfg['exclude']):
            return False
        if any(x in nm for x in s.cfg['include']):
            return True
        if h['cat'] not in s.cats:
            return False
        if h.get('hot') and not s.cfg['hot_hooks'] and s.cfg['mode'] != 'full':
            return False
        return True

    def install(s):
        n_ok = n_missing = 0
        clock_cands = []
        for h in s.catalog['hooks']:
            if h['module'] == 'static':
                a = s.static_syms.get(h['mangled'])
            else:
                m = s.mods.get(h['module'])
                a = s.cro_addrs(m).get(h['mangled']) if m else None
            if h['cat'] == 'clock':
                if a:
                    clock_cands.append((h, a))
                continue
            if not s.want_hook(h):
                continue
            if not a:
                n_missing += 1
                s.log.write({'t': 'hook', 'f': s.frame, 'name': h['name'], 'status': 'not exported here'})
                continue
            hk = Hook('cro' if h['module'] != 'static' else 'func', a, h, h['name'], h['cat'],
                      abi.plan(h['name']), h.get('ret') and s.cfg['return_values'], bool(a & 1))
            if s.add(hk):
                n_ok += 1
                s.log.write({'t': 'hook', 'f': s.frame, 'name': h['name'], 'cat': h['cat'], 'addr': '0x%08X' % a,
                             'status': 'on'})
        # the frame clock
        want = s.cfg['clock']
        s.clock_hook = None
        clock_cands.sort(key=lambda x: x[0].get('prio', 99))
        for h, a in clock_cands:
            if want == 'auto' or want in h['name'] or want == '0x%08X' % a:
                s.clock_hook = Hook('clock', a, h, h['name'], 'clock', thumb=bool(a & 1))
                break
        if want not in ('auto', 'none') and s.clock_hook is None:
            try:
                a = int(want, 16)
                s.clock_hook = Hook('clock', a, None, 'clock@0x%08X' % a, 'clock')
            except ValueError:
                pass
        if s.clock_hook and want != 'none':
            if s.add(s.clock_hook):
                s.note('[trace] frame clock: %s at 0x%08X' % (s.clock_hook.name, s.clock_hook.addr))
            else:
                s.clock_hook = None
        if not s.clock_hook:
            s.note('[trace] no frame clock hook: frames counted from the traced enemies\' per-frame updates')
        s.note('[trace] %d framework hooks on, %d not exported by this game version' % (n_ok, n_missing))
        s.install_enemies()

    def install_enemies(s):
        ef = s.mods.get('enemy_fs')
        if not ef or not s.map:
            return
        segs = s.map.get('file_segments') or None
        to_rt = (lambda off: ef.to_runtime(off, segs)) if segs else (lambda off: ef.base + off)
        s.to_rt = to_rt
        s.kinds_hooked = set()
        n = 0
        for kind, v in s.map['kinds'].items():
            if s.kinds and kind not in s.kinds:
                continue
            a = to_rt(v['create'])
            if s.add(Hook('create', a, {'kind': kind}, 'create:' + kind, 'spawn', want_ret=True,
                          plan=abi.plan('create(app::EnemyModuleAccessor&, int, int)'))):
                n += 1
            if s.cfg['eager_kinds'] or s.kinds:
                n += s.install_kind(kind)
        s.note('[trace] %d enemy breakpoints in enemy_fs.cro (map %s, base 0x%08X)%s' % (
            n, s.map['label'], ef.base, '' if (s.cfg['eager_kinds'] or s.kinds) else
            '; a kind\'s state hooks go in when its first one spawns'))

    def install_kind(s, kind):
        """the state / slot breakpoints of one kind"""
        if kind in s.kinds_hooked or not s.map or kind not in s.map['kinds']:
            return 0
        s.kinds_hooked.add(kind)
        v = s.map['kinds'][kind]
        to_rt = s.to_rt
        n = 0
        if True:
            if 'state' not in s.cats:
                return 0
            for sid, fns in v['states'].items():
                for role in ('enter', 'exit', 'update'):
                    off = fns.get(role)
                    if not off or (role == 'update' and not s.state_updates):
                        continue
                    if s.add(Hook('state', to_rt(off), {'kind': kind, 'state': int(sid), 'role': role},
                                  '%s:%s:%s' % (kind, sid, role), 'state')):
                        n += 1
            for slot, off in v['slots'].items():
                if not isinstance(off, int) or slot == 'death_state_id':
                    continue
                if slot in ('update', 'every_frame') and not s.state_updates:
                    continue
                if s.add(Hook('slot', to_rt(off), {'kind': kind, 'slot': slot}, '%s:slot:%s' % (kind, slot), 'state')):
                    n += 1
        return n

    def uninstall_module(s, m):
        lo, hi = m.range()
        for a in [a for a in s.bp if lo <= a < hi]:
            del s.bp[a]
        s.t.forget_range(lo, hi)

    # ------------------------------------------------------------------------------------------------ reading
    def rd(s, a, n):
        if not a:
            return None
        return s.t.try_read(a, n)

    def u32(s, a):
        b = s.rd(a, 4)
        return struct.unpack('<I', b)[0] if b else None

    def where(s, addr):
        for m in s.mods.values():
            if m.contains(addr):
                segs = s.map.get('file_segments') if (s.map and m.name == 'enemy_fs') else None
                fo = m.to_file(addr, segs) if segs else addr - m.base
                if m.name in ('|static|', 'static'):
                    return 'code.bin:0x%08X' % addr
                return '%s+0x%X' % (m.name, fo)
        return '0x%08X' % addr

    def kind_name(s, idx):
        return s.map_kinds_by_index.get(idx, 'kind%d' % idx if isinstance(idx, int) else None)

    def instance(s, inst, kind_hint=None):
        """the instance record; first sight: module pointers, a raw dump"""
        info = s.instances.get(inst)
        if info:
            return info
        b = s.rd(inst, 0x20)
        if not b:
            return None
        acc, state, kidx, var = struct.unpack_from('<IIII', b, 4)
        info = {'inst': inst, 'acc': acc, 'kind': s.kind_name(kidx) or kind_hint, 'kidx': kidx, 'var': var,
                'first': s.frame, 'last_raw': s.frame, 'mods': {}, 'updates': 0}
        offs = (s.map or {}).get('accessor') or {v: k for k, v in MODULE_OFFS.items()}
        if offs and acc:
            lo, hi = min(offs.values()), max(offs.values()) + 4
            mb = s.rd(acc + lo, hi - lo)
            if mb:
                for nm, off in offs.items():
                    p = struct.unpack_from('<I', mb, off - lo)[0]
                    if 0x00100000 <= p < 0x40000000:
                        info['mods'][nm] = p
                        s.modptr.setdefault(p, (inst, nm))
        post = info['mods'].get('Posture')
        info['posture'] = post
        ke = info['mods'].get('KineticEnergy')
        # the movement energy's parameter block: [[[[acc + KineticEnergy] + 8] + 0] + 4] (+0x08 .. +0x44 the words
        # the behaviours write; base Goomba notice-hop enter: ldr [+8], ldr [+0], ldr [+4], vstr [+0x20])
        e1 = s.u32(ke + 8) if ke else None
        e2 = s.u32(e1) if e1 else None
        info['energy'] = s.u32(e2 + 4) if e2 else None
        s.instances[inst] = info
        s.raw(inst, info, 'first sight')
        return info

    def raw(s, inst, info, why):
        kd = s.map['kinds'].get(info['kind'], {}) if s.map else {}
        size = max(s.cfg['raw_size'], kd.get('object_size') or 0)
        b = s.rd(inst, min(size, 0x800))
        ev = {'t': 'raw', 'f': s.frame, 'inst': '0x%08X' % inst, 'kind': info['kind'], 'why': why,
              'this': b.hex() if b else None}
        for nm in ('Posture', 'Damage', 'KineticEnergy'):
            p = info['mods'].get(nm)
            if p:
                bb = s.rd(p, 0x100)
                ev[nm] = bb.hex() if bb else None
        ev['mods'] = {k: '0x%08X' % v for k, v in info['mods'].items()}
        s.log.write(ev)
        info['last_raw'] = s.frame

    def snapshot(s, inst, info):
        b = s.rd(inst, 0x200)
        if not b:
            return {}
        state, kidx, var = struct.unpack_from('<III', b, 8)
        mx, my = struct.unpack_from('<ff', b, 0x14)
        out = {'state_field': state, 'var': var, 'move': [rf(mx), rf(my)]}
        kd = s.map['kinds'].get(info['kind'], {}) if s.map else {}
        flds = {}
        for off in kd.get('fields', []):
            if off + 4 <= len(b):
                w = struct.unpack_from('<I', b, off)[0]
                flds['%x' % off] = [w, rf(f32(w))]
        out['fields'] = flds
        if info.get('posture'):
            p = s.rd(info['posture'], 0x64)
            if p:
                out['pos'] = [rf(v) for v in struct.unpack_from('<3f', p, 0x14)]
                out['lr'] = rf(struct.unpack_from('<f', p, 0x60)[0])
        if info.get('energy'):
            e = s.rd(info['energy'], 0x48)
            if e:
                out['energy'] = [rf(v) for v in struct.unpack('<18f', e)]
        return out

    def owner_of(s, ptr):
        """an enemy instance for a Behavior / module pointer"""
        if ptr in s.instances:
            return s.instances[ptr]
        if ptr in s.modptr:
            return s.instances.get(s.modptr[ptr][0])
        return None

    # ------------------------------------------------------------------------------------------------ handlers
    def on_stop(s, stop):
        regs = s.t.read_regs()
        pc = regs.get('r15', 0)
        hooks = list(s.bp.get(pc & ~1, []))
        for h in hooks:
            try:
                s.handle(h, regs)
            except (rsp.RSPError, struct.error) as e:
                s.log.write({'t': 'note', 'f': s.frame, 'msg': 'handler error at %s: %s' % (h.name, e)})
            h.count += 1
            h.window += 1
            now = time.time()
            if now - h.wstart > s.cfg['hot_window']:
                rate = h.window / (now - h.wstart)
                if h.kind not in ('clock', 'ret', 'state', 'slot', 'create') and rate > s.cfg['hot_limit'] / \
                        s.cfg['hot_window']:
                    s.drop(h)
                    s.log.write({'t': 'hook', 'f': s.frame, 'name': h.name, 'status': 'disabled (hot: %.0f/s)' % rate})
                h.window, h.wstart = 0, now
        return pc

    def handle(s, h, regs):
        k = h.kind
        if k == 'clock':
            s.frame += 1
            if s.cfg['clock_log_every'] and s.frame % s.cfg['clock_log_every'] == 0:
                s.log.write({'t': 'clock', 'f': s.frame})
            s.periodic()
            return
        if k == 'ret':
            s.on_return(h, regs)
            return
        if k == 'create':
            s.call(h, regs, extra={'kind_hook': h.data['kind']})
            return
        if k in ('state', 'slot'):
            s.on_state(h, regs)
            return
        s.call(h, regs)

    def on_state(s, h, regs):
        inst = regs['r0']
        info = s.instance(inst, h.data['kind'])
        if not info:
            return
        if s.kinds and info['kind'] not in s.kinds:
            return
        if info['kind'] != h.data['kind']:
            # a function shared by several kinds: keep the instance's own kind
            pass
        role = h.data.get('role') or h.data.get('slot')
        if not s.clock_hook and role in ('update',) and s.frame_owner(inst):
            s.frame += 1
            s.periodic()
        if role == 'update':
            info['updates'] += 1
            if info['updates'] % max(1, s.cfg['update_every']):
                return
        ev = {'t': 'state' if h.kind == 'state' else 'slot', 'f': s.frame, 'kind': info['kind'],
              'inst': '0x%08X' % inst, 'role': role, 'fn': s.where(h.addr)}
        if h.kind == 'state':
            ev['state'] = h.data['state']
        ev.update(s.snapshot(inst, info))
        s.log.write(ev)
        s.last_ctx = (inst, info['kind'], ev.get('state'), s.frame)
        if s.cfg['raw_every'] and s.frame - info['last_raw'] >= s.cfg['raw_every']:
            s.raw(inst, info, 'periodic')

    def frame_owner(s, inst):
        if not hasattr(s, '_fo') or s._fo not in s.instances:
            s._fo = inst
        return s._fo == inst

    def call(s, h, regs, extra=None):
        d = h.data
        this = regs.get('r0')
        plan_ = h.plan or []
        has_this = plan_ and plan_[0][0] == 'this'
        own = s.owner_of(this) if has_this else None
        if s.kinds and own and own['kind'] not in s.kinds:
            return
        sregs = s.t.read_sregs(16) if abi.needs_sregs(plan_) else None
        args = abi.decode(plan_, regs, sregs, s.rd)
        ev = {'t': 'call', 'f': s.frame, 'cat': h.cat, 'hook': h.name, 'caller': s.where(regs.get('r14', 0)),
              'args': args, 'raw': ['0x%08X' % regs.get('r%d' % i, 0) for i in range(4)]}
        if own:
            ev['owner'] = {'inst': '0x%08X' % own['inst'], 'kind': own['kind']}
            if this in s.modptr and this != own['inst']:
                ev['owner']['via'] = s.modptr[this][1]
        elif s.last_ctx and s.last_ctx[3] == s.frame and s.where(regs.get('r14', 0)).startswith('enemy_fs'):
            ev['owner'] = {'inst': '0x%08X' % s.last_ctx[0], 'kind': s.last_ctx[1], 'inferred': True}
        if s.last_ctx and s.last_ctx[3] == s.frame:
            ev['ctx_state'] = s.last_ctx[2]
        if extra:
            ev.update(extra)
        if 'InnerEnemyAttackParam' in h.name:
            ev['attack'] = s.attack_fields(args.get('a0_raw'))
        if h.want_ret or h.kind == 'create':
            s.call_id += 1
            ev['id'] = s.call_id
            lr = regs.get('r14', 0)
            if lr:
                s.pending.setdefault(lr & ~1, []).append((regs.get('r13'), s.call_id, h, s.frame))
                if (lr & ~1) not in s.bp or not any(x.kind == 'ret' for x in s.bp[lr & ~1]):
                    s.add(Hook('ret', lr & ~1, None, 'ret', 'ret', thumb=bool(lr & 1)))
        s.log.write(ev)

    def attack_fields(s, hexraw):
        if not hexraw:
            return None
        b = bytes.fromhex(hexraw)
        out = {}
        for i in range(len(b) // 4):
            w = struct.unpack_from('<I', b, 4 * i)[0]
            nm = ATTACK_NAMES[i] if i < len(ATTACK_NAMES) else 'f%d' % i
            out[nm] = rf(f32(w)) if i in ATTACK_FLOATS else struct.unpack('<i', struct.pack('<I', w))[0]
        return out

    def on_return(s, h, regs):
        a = h.addr & ~1
        lst = s.pending.get(a, [])
        sp = regs.get('r13')
        hit = None
        for i, (esp, cid, hk, fr) in enumerate(lst):
            if esp == sp:
                hit = lst.pop(i)
                break
        if hit is None:
            return
        _esp, cid, hk, fr = hit
        r0 = regs.get('r0', 0)
        ev = {'t': 'ret', 'f': s.frame, 'id': cid, 'hook': hk.name, 'r0': r0, 'r0_s': struct.unpack(
            '<i', struct.pack('<I', r0))[0]}
        try:
            ev['s0'] = rf(s.t.read_sregs(1)[0])
        except rsp.RSPError:
            pass
        if hk.kind == 'create' and r0:
            if hk.data['kind'] not in getattr(s, 'kinds_hooked', ()):
                s.log.write({'t': 'hook', 'f': s.frame, 'name': hk.data['kind'], 'status': 'state hooks on (%d)' %
                             s.install_kind(hk.data['kind'])})
            info = s.instance(r0, hk.data['kind'])
            if info:
                ev['spawn'] = {'inst': '0x%08X' % r0, 'kind': info['kind'], 'var': info['var']}
                s.log.write({'t': 'spawn', 'f': s.frame, 'inst': '0x%08X' % r0, 'kind': info['kind'],
                             'var': info['var'], 'acc': '0x%08X' % info['acc'], 'id': cid})
        s.log.write(ev)
        if not lst:
            s.pending.pop(a, None)
            for x in list(s.bp.get(a, [])):
                if x.kind == 'ret':
                    s.drop(x)

    def periodic(s):
        # stale return breakpoints (a call that never returned to its caller frame)
        for a, lst in list(s.pending.items()):
            lst[:] = [e for e in lst if s.frame - e[3] < 600]
            if not lst:
                s.pending.pop(a, None)
                for x in list(s.bp.get(a, [])):
                    if x.kind == 'ret':
                        s.drop(x)
        if s.dump_at is not None and s.frame >= s.dump_at:
            s.dump_at = None
            s.dump_all('stage load')

    # ------------------------------------------------------------------------------------------------ dumps
    def rtti_name(s, obj):
        vt = s.u32(obj)
        if not vt or not (0x00100000 <= vt < 0x40000000):
            return None
        ti = s.u32(vt - 4)
        if not ti or not (0x00100000 <= ti < 0x40000000):
            return None
        np_ = s.u32(ti + 4)
        if not np_:
            return None
        b = s.rd(np_, 64)
        if not b:
            return None
        n = b.split(b'\0')[0]
        if not n or any(c < 0x20 or c > 0x7E for c in n):
            return None
        return n.decode('latin1')

    def dump_params(s):
        acc_p = s.singletons.get('EnemyParamAccessor')
        acc = s.u32(acc_p) if acc_p else None
        if not acc or not s.map:
            s.note('[dump] no EnemyParamAccessor (singleton %s, map %s)' % (acc_p, bool(s.map)))
            return
        n = 0
        for kind, v in s.map['kinds'].items():
            obj = s.u32(acc + 0x60 + 4 * v['index'])
            if not obj:
                continue
            groups = []
            for m in (v.get('params') or {}).get('members', []):
                if m.get('type') != 'array':
                    continue
                cnt = s.u32(obj + m['offset'] + 8)
                data = s.u32(obj + m['offset'] + 0xC)
                if cnt is None or not data or cnt > 256:
                    continue
                b = s.rd(data, cnt * m['elem_size']) or b''
                ents = []
                for e in range(cnt):
                    row = []
                    for off, wd in zip(m['offsets'], m['widths']):
                        o = e * m['elem_size'] + off
                        if o + wd > len(b):
                            break
                        if wd == 4:
                            w = struct.unpack_from('<I', b, o)[0]
                            iv = struct.unpack('<i', struct.pack('<I', w))[0]
                            row.append(iv if -0x100000 < iv < 0x100000 else rf(f32(w)))
                        else:
                            row.append(int.from_bytes(b[o:o + wd], 'little'))
                    ents.append(row)
                groups.append({'index': m['index'], 'names': m.get('names'), 'count': cnt, 'values': ents,
                               'raw': b.hex()})
            s.log.write({'t': 'dump', 'f': s.frame, 'what': 'params', 'kind': kind, 'object': '0x%08X' % obj,
                         'groups': groups})
            n += 1
        s.note('[dump] params of %d kinds' % n)

    def dump_singletons(s, size=0x400):
        for nm, a in sorted(s.singletons.items()):
            p = s.u32(a)
            b = s.rd(p, size) if p else None
            s.log.write({'t': 'dump', 'f': s.frame, 'what': 'singleton', 'name': nm, 'slot': '0x%08X' % a,
                         'object': '0x%08X' % p if p else None, 'class': s.rtti_name(p) if p else None,
                         'raw': b.hex() if b else None})

    def dump_objects(s, root_name='InstanceList<GimmickControllerBase>', filt=('Gcon', 'Gimmick', 'Stage', 'Door',
                                                                              'Treasure', 'Enemy', 'Item'),
                     limit=1500, depth=4):
        """objects reachable from a singleton, identified by their RTTI class name (doors, chests, hazards ...)"""
        a = s.singletons.get(root_name)
        if not a:
            s.note('[dump] no %s' % root_name)
            return
        seen, todo, found = set(), [(s.u32(a), 0)], 0
        if root_name.startswith('InstanceList'):
            todo.append((a, 0))
        while todo and found < limit:
            p, d = todo.pop()
            if not p or p in seen or not (0x00100000 <= p < 0x40000000) or p & 3:
                continue
            seen.add(p)
            b = s.rd(p, 0x100)
            if not b:
                continue
            nm = s.rtti_name(p)
            if nm and any(x in nm for x in filt):
                found += 1
                s.log.write({'t': 'dump', 'f': s.frame, 'what': 'object', 'root': root_name, 'class': nm,
                             'addr': '0x%08X' % p, 'raw': b.hex()})
            if d < depth:
                for off in range(0, len(b), 4):
                    q = struct.unpack_from('<I', b, off)[0]
                    if 0x08000000 <= q < 0x40000000 and q not in seen:
                        todo.append((q, d + 1))
        s.note('[dump] %d objects reachable from %s' % (found, root_name))

    def dump_all(s, why):
        s.note('[dump] %s' % why)
        s.dump_singletons()
        s.dump_params()
        s.dump_objects()
        for root in ('FieldSmashManager', 'EnemyGenerator', 'ItemManager'):
            s.dump_objects(root, depth=2, limit=400)

    # ------------------------------------------------------------------------------------------------ loop
    def rescan(s):
        old = {n: m.base for n, m in s.mods.items()}
        for n, m in list(s.mods.items()):
            h = s.t.try_read(m.base + 0x80, 4)
            if h != cro.MAGIC:
                s.log.write({'t': 'module', 'f': s.frame, 'name': n, 'base': '0x%08X' % m.base, 'status': 'gone'})
                s.uninstall_module(m)
                del s.mods[n]
        st = s.static_module()
        if st and not all(n in s.mods for n in ('enemy_fs', 'main_field')):
            s.loc.chain(st, s.mods)
            s.loc.remember(s.mods)
        new = [n for n in s.mods if n not in old or s.mods[n].base != old.get(n)]
        for n in new:
            s.log.write({'t': 'module', 'f': s.frame, 'name': n, 'base': '0x%08X' % s.mods[n].base, 'status': 'loaded'})
        if 'enemy_fs' in new or any(n in new for n in ('main_field', 'menu')):
            if 'enemy_fs' in new:
                s.choose_map()
            s.reinstall_cro_hooks(new)
        if 'main_field' in new and s.cfg['dump_on_stage']:
            s.dump_at = s.frame + s.cfg['dump_delay']

    def cro_addrs(s, m):
        if not hasattr(s, '_cro_addr_cache'):
            s._cro_addr_cache = {}
        key = (m.name, m.base)
        if key not in s._cro_addr_cache:
            s._cro_addr_cache[key] = s.module_addrs(m, [h for h in s.catalog['hooks'] if h['module'] == m.name])
        return s._cro_addr_cache[key]

    def reinstall_cro_hooks(s, names):
        for h in s.catalog['hooks']:
            if h['module'] in names and s.want_hook(h):
                m = s.mods[h['module']]
                a = s.cro_addrs(m).get(h['mangled'])
                if a:
                    s.add(Hook('cro', a, h, h['name'], h['cat'], abi.plan(h['name']), False))
        if 'enemy_fs' in names:
            s.install_enemies()

    def setup(s):
        s.connect()
        s.find_modules()
        if not s.static_module():
            s.note('[trace] static.crs not found in RAM yet: is the game running (past the title screen)?')
        s.resolve_static()
        s.choose_map()
        if not getattr(s, '_header_done', False):
            s.header()
            s._header_done = True
        s.install()
        for n, m in s.mods.items():
            s.log.write({'t': 'module', 'f': s.frame, 'name': n, 'base': '0x%08X' % m.base, 'status': 'found'})

    def teardown(s):
        if not s.t or not s.client.sock:
            return
        try:
            if s.t.running:
                s.t.halt(3)
        except (rsp.RSPError, OSError, socket.timeout):
            pass
        try:
            s.t.remove_all()
        finally:
            s.t.detach()
            s.client.close()
            s.say('[trace] breakpoints removed, detached')

    def run(s, one_shot=None, partial=None):
        s.open()
        t_end = time.time() + s.cfg['duration'] if s.cfg['duration'] else None
        try:
            while True:
                try:
                    s.setup()
                    if one_shot:
                        one_shot(s)
                        return
                    s.loop(t_end)
                    return
                except (rsp.Disconnected, ConnectionError, socket.timeout, OSError) as e:
                    s.note('[trace] connection lost (%s)' % e)
                    s.client.close()
                    s.bp.clear()
                    s.t.bps.clear()
                    s.pending.clear()
                    if not s.cfg['reconnect']:
                        return
                    while True:
                        time.sleep(2)
                        try:
                            socket.create_connection((s.cfg['host'], s.cfg['port']), timeout=2).close()
                            break
                        except OSError:
                            continue
                    s.note('[trace] reconnecting')
        except KeyboardInterrupt:
            s.note('[trace] Ctrl+C: stopping')
            if partial:
                try:
                    partial(s)
                except Exception as e:          # the summary of what is known must not hide the teardown
                    s.say('[trace] (partial summary failed: %s)' % e)
        finally:
            if getattr(s, 'loc', None):
                s.log.write({'t': 'note', 'f': s.frame, 'msg': 'packet accounting', 'steps': s.loc.steps.rows,
                             'packets': s.client.n_packets, 'latency': s.loc.latency, 'how': s.loc.how})
            s.teardown()
            if s.log:
                s.log.close()
                s.say('[trace] log: %s (%d events)' % (s.cfg['out'], s.log.count))

    def loop(s, t_end=None):
        if s.t.running:
            st = None
        else:
            regs = s.t.read_regs()
            st = s.t.cont(regs.get('r15'))
        idle = time.time()
        while not s.stop_flag:
            if s.log.capped:
                return
            if t_end and time.time() > t_end:
                s.note('[trace] duration reached')
                return
            if st is None:
                st = s.t.wait(1.0)
            if st is None:
                if time.time() - idle > 30:
                    s.log.write({'t': 'note', 'f': s.frame, 'msg': 'no breakpoint hit for 30 s (paused, or in menus)'})
                    idle = time.time()
                if time.time() > s.next_rescan:
                    s.next_rescan = time.time() + s.cfg['rescan_every']
                    stop = s.t.halt()
                    if stop is not None:
                        pc = s.handle_stop(stop)
                        s.rescan()
                        st = s.t.cont(pc)
                continue
            idle = time.time()
            if st.exited:
                s.note('[trace] the game exited (%s)' % st.raw)
                return
            pc = s.handle_stop(st)
            if time.time() > s.next_rescan:
                s.next_rescan = time.time() + s.cfg['rescan_every']
                s.rescan()
            st = s.t.cont(pc)

    def handle_stop(s, st):
        regs_pc = s.on_stop(st)
        return regs_pc
