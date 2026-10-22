#!/usr/bin/env python3
"""Runs the game functions tools/kind_expand.py patches, in unicorn, on the patched and the unpatched RPX.

  python3 tools/kind_expand_test.py PATCHED.rpx ORIGINAL.rpx [KINDS.json] [--others ARGS_FILE ...]

PATCHED = ORIGINAL + $(python3 tools/kind_expand.py) (and any other caves); ORIGINAL = the base the
generator read (build/cross_f.rpx). --others: files holding other cave scripts' rpx_patch.py
arguments, checked for overlapping words.

What it checks (every game kind 0x00-0x40 against the unpatched RPX, the new kinds against their base):
- every patched word: in-place instructions decode (capstone) to the intended instruction and their
  originals to the expected ones; the copied vl cases differ from the base's only in the planned
  fields; the relocated RAM immediates moved by their array's offset; no relocation is left on a
  patched in-place word; no overlap with the other caves; the switch tables point at instructions;
- the param manager: constructor (allocation sizes), loader (kind -> fighter_param entry map, the
  arrays it clears), vl load / unload of every kind twice (call log, file names, per-kind arrays,
  equipment-object field, mirror), the new kinds (base loaded too and released), unload-all;
- the six switches' dispatch for every kind 0x00-capacity, and that no case reads the scratch
  register whose value changed (r0 / r12);
- descriptor getter and the motion table (0x02EA9064 builds it into the new kind's own copy),
  specializer, names, size / sound-class tables, character id -> UI name, kind -> character id, the
  AI amiibo-learning guard.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpx_patch as R  # noqa: E402
import kind_expand as K  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
import capstone  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

REGS = [getattr(__import__('unicorn.ppc_const', fromlist=['x']), 'UC_PPC_REG_%d' % i) for i in range(32)]
HEAP, STRUCTS, STACK = 0x60000000, 0x68000000, 0x70000000
BLR = 0x4E800020
MD = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
MDD = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
MDD.detail = True

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


class Emu:
    """an RPX in unicorn, with Python stubs (the stubbed function's first word becomes blr)"""

    def __init__(self, path):
        self.mu = machine(path)
        self.mu.mem_map(HEAP, 0x01000000)
        self.mu.mem_map(STRUCTS, 0x00400000)
        self.mu.mem_map(STACK, 0x00100000)
        d, _s, _e, secs = R.load(path)
        for sec in secs:                      # .bss (machine() maps the file's sections only)
            if sec[1] == 8 and sec[3]:
                lo_ = (sec[3] + 0xFFF) & ~0xFFF
                self.mu.mem_map(lo_, ((sec[3] + sec[5] + 0xFFF) & ~0xFFF) - lo_)
        self.heap = HEAP
        self.nstruct = 0
        self.log = []
        self.sid = {}

    def r(self, i):
        return self.mu.reg_read(REGS[i])

    def w(self, a):
        return struct.unpack('>I', bytes(self.mu.mem_read(a, 4)))[0]

    def setw(self, a, v):
        self.mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))

    def cstr(self, a):
        if not a:
            return None
        b = bytes(self.mu.mem_read(a, 128))
        return b[:b.index(b'\0')].decode('latin1')

    def alloc(self, n, fill=b'\xA5'):
        a = self.heap
        self.heap += (n + 0x3F) & ~0x1F
        self.mu.mem_write(a, fill * n)
        return a

    def stub(self, addr, fn):
        self.mu.mem_write(addr, struct.pack('>I', BLR))

        def cb(mu, a, size, ud):
            v = fn(self)
            if v is not None:
                mu.reg_write(UC_PPC_REG_3, v & 0xFFFFFFFF)
        self.mu.hook_add(UC_HOOK_CODE, cb, None, addr, addr)

    def call(self, fn, *args, until=RET, count=200000):
        for i, v in enumerate(args):
            self.mu.reg_write(REGS[3 + i], v & 0xFFFFFFFF)
        self.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
        self.mu.reg_write(UC_PPC_REG_LR, RET)
        self.mu.emu_start(fn, until, count=count)
        return self.mu.reg_read(UC_PPC_REG_3)

    def fake_struct(self):
        """a parsed vl struct: words (id << 16) | offset (positive, so the vl tail's per-kind blocks run)"""
        self.nstruct += 1
        a = STRUCTS + 0x1000 * self.nstruct
        self.mu.mem_write(a, b''.join(struct.pack('>I', (self.nstruct << 16) | o) for o in range(0, 0x1000, 4)))
        self.sid[a] = self.nstruct
        return a


def decode(word, addr):
    ins = list(MD.disasm(struct.pack('>I', word), addr))
    return ('%s %s' % (ins[0].mnemonic, ins[0].op_str)).strip() if ins else None


def same_instruction(word, text, addr):
    """capstone's reading of `word` assembles (ppcasm) back to the word, and `text` too"""
    cs = decode(word, addr)
    if cs is None:
        return False, None
    try:
        return K.one(addr, text) == word, cs
    except Exception:
        return False, cs


def reads_before_write(img_mem, start, regs, limit=12):
    """does the code at start read one of regs before writing it (straight-line, up to the first branch)?
    (capstone has no register access info for PPC: operands are read from the text)"""
    a = start
    for _ in range(limit):
        ins = list(MD.disasm(img_mem(a, 4), a))
        if not ins:
            return False
        m, ops = ins[0].mnemonic, [x.strip() for x in ins[0].op_str.split(',')] if ins[0].op_str else []
        names = []
        for o in ops:
            base = o[o.index('(') + 1:-1] if '(' in o else o
            names.append(base if base.startswith('r') and base[1:].isdigit() else None)
        lit0 = (m in ('addi', 'addis') and len(ops) == 3 and ops[1] == 'r0') or \
            any('(r0)' in o for o in ops)          # rA = r0 is the literal 0 there
        if m.startswith(('st', 'cmp', 'mt', 'b', 'tw')):
            rd, wr = {x for x in names if x}, set()
        else:
            rd, wr = {x for x in names[1:] if x}, {names[0]} if names and names[0] else set()
        if lit0:
            rd.discard('r0')
        if rd & regs:
            return True
        regs = regs - wr
        if not regs or m.startswith('b'):
            return False
        a += 4
    return False


def main():
    argv = sys.argv[1:]
    others = []
    while '--others' in argv:
        i = argv.index('--others')
        others.append(argv[i + 1])
        del argv[i:i + 2]
    patched, original = argv[0], argv[1]
    spec = argv[2] if len(argv) > 2 else K.SPEC
    B, info = K.build(spec, original)
    cap, count, kinds = info['capacity'], info['count'], info['kinds']
    lay = info['mgr_layout']
    img = B.img
    pimg = K.Image(patched)

    # ------------------------------------------------------------ the words
    print('# patch words')
    bad = [hex(a) for a, w in B.words.items() if pimg.w(a) != w]
    check('every generated word is in the patched RPX', bad, [])
    bad = []
    for a in B.inplace:
        what = B.what[a]
        w = B.words[a]
        if isinstance(what, str):
            ok, cs = same_instruction(w, what, a)
            if not ok:
                bad.append((hex(a), what, cs))
        elif what[0] == 'ram':
            arr = what[1]
            d = K.sx16(w) - K.sx16(img.w(a))
            if d != lay[arr][1] - lay[arr][0] or (w ^ img.w(a)) & 0xFFFF0000:
                bad.append((hex(a), what))
            elif decode(w, a) is None:
                bad.append((hex(a), 'undecodable'))
    check('in-place words (%d) decode to the intended instructions / moved immediates' % len(B.inplace), bad, [])
    # cave code: asm text, copies
    bad, ncopy, ncode = [], 0, 0
    for a, what in B.what.items():
        if a < K.CAVE:
            continue
        w = B.words[a]
        if isinstance(what, tuple) and what[0] == 'copy':
            ncopy += 1
            src, change = what[1], what[2]
            ow, ot = img.w(src), decode(img.w(src), src)
            nt = decode(w, a)
            if change == 'same':
                if w != ow:
                    bad.append((hex(a), 'changed', ot, nt))
            elif change in ('branch', 'fallthrough'):
                if nt is None or not nt.split()[0].startswith('b'):
                    bad.append((hex(a), nt))
                elif change == 'branch' and K.branch_target(a, w) != K.branch_target(src, ow) and \
                        not (ow >> 26 == 16):
                    bad.append((hex(a), 'target', ot, nt))
            else:
                if (w ^ ow) & 0xFFFF0000 or nt is None or nt.split()[0] != ot.split()[0]:
                    bad.append((hex(a), change, ot, nt))
        elif isinstance(what, str) and not what.startswith(('table', 'switch', 'descriptor', 'motion', 'strings', 'data')):
            ncode += 1
            ok, cs = same_instruction(w, what, a)
            if not ok:
                bad.append((hex(a), what, cs))
    check('cave code: %d assembled words and %d copied case words decode as intended' % (ncode, ncopy), bad, [])
    # relocations left on in-place words
    rel = pimg.relocs()
    left = [hex(a) for a in B.inplace if a in rel]
    check('no relocation left on a patched in-place word (%d moved)' % len(B.reloc_args()), left, [])
    # overlap with the other caves
    mine = set(B.words)
    for path in others:
        theirs, their_rel = set(), set()
        for t in open(path).read().split():
            if t.startswith('grow:'):
                continue
            if t.startswith('reloc:'):
                lo_, hi_ = t[6:].split('=')[0].split('-')
                their_rel.update(range(int(lo_, 16), int(hi_, 16), 4))
                continue
            theirs.add(int(t.split('=')[0], 16))
        check('no overlap with %s (%d words)' % (os.path.basename(path), len(theirs)),
              sorted(hex(a) for a in mine & (theirs | their_rel)), [])
    check('cave inside the grown space', (min(a for a in mine if a >= K.CAVE) >= K.CAVE, info['cave_end'] <= K.LIMIT),
          (True, True))

    # ------------------------------------------------------------ switches
    print('# switches')
    P, O = Emu(patched), Emu(original)
    for name, (cmp_, reg, shape, table) in K.SWITCHES.items():
        n = {'r0': 8, 'r0li': 9, 'r12': 7}[shape]

        def target(E, k):
            # step from the compare until the code leaves the dispatch and the game's b-table
            E.mu.reg_write(REGS[reg], k)
            E.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
            pc = cmp_
            for _ in range(n + 2):
                E.mu.emu_start(pc, 0, count=1)
                pc = E.mu.reg_read(UC_PPC_REG_PC)
                if not (cmp_ <= pc < cmp_ + 4 * n or table <= pc < table + 4 * K.OLD_N):
                    return pc
            return None
        tab, default = info['switch_tables'][name]
        diff = [k for k in range(K.OLD_N) if target(P, k) != target(O, k)]
        check('%s: kinds 0x00-0x40 dispatch as before' % name, diff, [])
        targets, _ = K.switch_targets(img, name)
        for r in kinds:
            want = {'specializer': targets[r['bkind']], 'descriptor': r['desc_case'], 'vl_load': r['load_case'],
                    'vl_unload': r['unload_case']}.get(name, targets[r['bkind']] if r['ai'] == 'base' else default)
            check('%s: kind 0x%X -> 0x%08X (%s)' % (name, r['kind'], want, 'base %s' % info['names'][r['bkind']]
                                                    if want in targets else 'own case' if want != default else 'default'),
                  target(P, r['kind']), want)
        unused = [k for k in range(count, cap + 3) if target(P, k) != default]
        check('%s: unused kinds 0x%X-0x%X and past the capacity -> default' % (name, count, cap + 2), unused, [])
        sregs = {'r12'} if shape == 'r12' else {'r0'}
        readers = [hex(t) for t in set(targets) | {default} if reads_before_write(img.blob, t, set(sregs))]
        check('%s: no case reads %s before writing it (it now holds the target)' % (name, '/'.join(sregs)), readers, [])

    # ------------------------------------------------------------ specializer, descriptor, names, tables
    print('# getters')
    spec_fn, desc_fn = 0x02E669F0, 0x02E4313C
    check('specializer kinds 0x00-0x40 unchanged',
          [k for k in range(K.OLD_N) if P.call(spec_fn, 0, k) != O.call(spec_fn, 0, k)], [])
    desc_ok = [k for k in range(K.OLD_N) if P.call(desc_fn, 0, k) != O.call(desc_fn, 0, k)]
    check('descriptor kinds 0x00-0x40 unchanged', desc_ok, [])
    for r in kinds:
        b = r['bkind']
        check('specializer 0x%X = %s\'s singleton' % (r['kind'], info['names'][b]), P.call(spec_fn, 0, r['kind']),
              O.call(spec_fn, 0, b))
        d = P.call(desc_fn, 0, r['kind'])
        check('descriptor 0x%X is its own copy' % r['kind'], d, r['desc'])
        bd = O.call(desc_fn, 0, r['dkind'])
        words = [P.w(d + 4 * i) for i in range(K.DESC_SIZE // 4)]
        bwords = [O.w(bd + 4 * i) for i in range(K.DESC_SIZE // 4)]
        check('  +0 = kind, +0x1C = 0', (words[0], words[7]), (r['kind'], 0))
        check('  other words = %s\'s' % info['names'][r['dkind']],
              [i for i in range(K.DESC_SIZE // 4) if i not in (0, 1, 7) and words[i] != bwords[i]], [])
        mi, bmi = words[1], bwords[1]
        check('  motion info: own main table, the rest = the base\'s',
              ([P.w(mi + 4 * i) for i in range(6)][0] != O.w(bmi), [P.w(mi + 4 * i) for i in range(1, 6)]),
              (True, [O.w(bmi + 4 * i) for i in range(1, 6)]))
        n = O.w(bmi + 4)
        check('  main motion table = the base\'s (%d motions)' % n,
              bytes(P.mu.mem_read(P.w(mi), 8 * n)) == bytes(O.mu.mem_read(O.w(bmi), 8 * n)), True)
    for k in (count, cap - 1, cap):
        check('specializer 0x%X -> 0' % k, P.call(spec_fn, 0, k), 0)
    abort = 0x04ADC364
    P.call(desc_fn, 0, cap, until=abort)
    check('descriptor 0x%X -> the abort (as past 0x40 before)' % cap, P.mu.reg_read(UC_PPC_REG_PC), abort)

    lower, capf = 0x0275DB24, 0x0275DB38
    check('names 0x00-0x40 unchanged', [k for k in range(K.OLD_N) if (P.cstr(P.call(lower, k)), P.cstr(P.call(capf, k)))
                                        != (O.cstr(O.call(lower, k)), O.cstr(O.call(capf, k)))], [])
    for r in kinds:
        check('names 0x%X' % r['kind'], (P.cstr(P.call(lower, r['kind'])), P.cstr(P.call(capf, r['kind']))),
              (r['name'], r['cap']))
    check('names of unused kinds = ""', {P.cstr(P.call(lower, k)) for k in range(count, cap)} | {''}, {''})
    getters = [0x02EA90E0, 0x02EA9104, 0x02EA9120, 0x02EA913C, 0x02EA9158]
    snd = 0x02AB8CB0
    check('size getters / sound class 0x00-0x40 unchanged',
          [k for k in range(K.OLD_N) if [P.call(g, 0, k) for g in getters] + [P.call(snd, k, 0), P.call(snd, k, 1)] !=
           [O.call(g, 0, k) for g in getters] + [O.call(snd, k, 0), O.call(snd, k, 1)]], [])
    for r in kinds:
        b = r['bkind']
        check('size getters / sound class 0x%X = %s\'s' % (r['kind'], info['names'][b]),
              [P.call(g, 0, r['kind']) for g in getters] + [P.call(snd, r['kind'], 0)],
              [O.call(g, 0, b) for g in getters] + [O.call(snd, b, 0)])
    check('size getters: unused kinds and the capacity -> 0',
          {P.call(g, 0, k) for g in getters for k in (count, cap - 1, cap, cap + 5)}, {0})
    chrname = 0x0293DCCC
    ids = list(range(0, 59)) + list(range(0xC8, 0xE4))
    check('character id -> UI name: the game\'s ids unchanged',
          [i for i in ids if P.cstr(P.call(chrname, i)) != O.cstr(O.call(chrname, i))], [])
    for r in kinds:
        if r['ui_id'] is not None:
            check('character id %d -> %r' % (r['ui_id'], r['ui_name']), P.cstr(P.call(chrname, r['ui_id'])), r['ui_name'])
    check('unknown character id -> null', P.call(chrname, 150), 0)

    # kind -> character id (0x0309FE50) on a fake database: entry i = id i, kind = i's kind
    def fake_db(E, pairs):
        ents = E.alloc(0x4C * len(pairs), b'\0')
        for i, (cid, kind) in enumerate(pairs):
            e = ents + 0x4C * i
            E.mu.mem_write(e + 3, bytes([cid]))
            E.setw(e + 0xC, 1 if cid else 0)
            E.setw(e + 0x10, kind)
        inner = E.alloc(0x10, b'\0')
        E.setw(inner + 8, len(pairs))
        E.setw(inner + 0xC, ents)
        db = E.alloc(4, b'\0')
        E.setw(db, inner)
        return db
    pairs = [(i, i - 1 if i else 0) for i in range(59)] + [(r['ui_id'], r['kind']) for r in kinds if r['ui_id']]
    dbs = (fake_db(P, pairs), fake_db(O, pairs))
    check('kind -> character id: kinds 0x00-0x40 unchanged',
          [k for k in range(K.OLD_N) if P.call(0x0309FE50, dbs[0], k) != O.call(0x0309FE50, dbs[1], k)], [])
    for r in kinds:
        if r['ui_id'] is not None:
            check('kind 0x%X -> character id %d' % (r['kind'], r['ui_id']), P.call(0x0309FE50, dbs[0], r['kind']), r['ui_id'])
    check('kind 0x%X (past the capacity) -> 0xFF' % cap, P.call(0x0309FE50, dbs[0], cap), 0xFF)

    # ------------------------------------------------------------ param manager
    print('# FighterParamManager')
    NEW, HEAPGET, DTOR, RES, SPRINTF, MEMSET = 0x03374578, 0x032D3E3C, 0x032D4200, 0x032D7220, 0x04ADA330, 0x04ADFE84
    SUBCTORS = (0x02E8F81C, 0x02E8F910, 0x02E8F9D4, 0x02E8FF78, 0x02E901E4)
    BINDERS = (0x02EBDD84, 0x02EBDD94, 0x02EBDDA4, 0x02EBDDB4, 0x02EBDDC4)
    load_t, _ = K.switch_targets(img, 'vl_load')
    unload_t, _ = K.switch_targets(img, 'vl_unload')

    def bls(a, stop):
        out = []
        while True:
            w = img.w(a)
            if w >> 26 == 18:
                if not w & 1:
                    break
                out.append(K.branch_target(a, w))
            a += 4
            if a == stop:
                break
        return out
    ALLOCF, PARSEF, FREEF, DESTF = {}, {}, {}, {}
    for k in range(K.OLD_N):
        b = bls(load_t[k], K.VL_TAIL)
        assert len(b) == 6 and b[0] == HEAPGET and b[3] == RES
        ALLOCF.setdefault(b[1], k)
        PARSEF.setdefault(b[4], k)
        u = bls(unload_t[k], K.VL_UNLOAD_TAIL)
        FREEF.setdefault(u[0], k)
        DESTF.setdefault(u[1], k)
    entries_order = list(range(count))[::-1]          # fighter_param.bin entries, not in kind order

    def setup(E):
        E.sizes = []

        def new(E):
            n = E.r(3)
            E.sizes.append(n)
            return E.alloc(n)
        E.stub(NEW, new)
        E.stub(HEAPGET, lambda E: 0x6FFF0000)
        E.stub(DTOR, lambda E: None)
        for s in SUBCTORS:
            E.stub(s, lambda E: E.r(3))

        def memset(E):
            E.memsets.append(E.r(4))
            E.mu.mem_write(E.r(3), b'\0' * E.r(4))
            return E.r(3)
        E.memsets = []
        E.stub(MEMSET, memset)

        def res(E):
            E.last_file = E.cstr(E.r(4))
            E.log.append(('file', E.last_file))
            return E.r(3)
        E.stub(RES, res)

        def fp_binder(E):
            mgr = E.r(4)
            ents = E.alloc(0x588 * len(entries_order), b'\0')
            for i, k in enumerate(entries_order):
                E.setw(ents + 0x588 * i, k)
            E.setw(mgr + 8, len(entries_order))
            E.setw(mgr + 0xC, ents)
        E.stub(BINDERS[0], fp_binder)
        for s in BINDERS[1:]:
            E.stub(s, lambda E: None)

        def sprintf(E):
            fmt = E.cstr(E.r(5))
            assert fmt == '%s', fmt
            s = E.cstr(E.r(6)).encode() + b'\0'
            E.mu.mem_write(E.r(3), s[:E.r(4)])
            return len(s) - 1
        E.stub(SPRINTF, sprintf)
        for f, k in ALLOCF.items():
            E.stub(f, lambda E, k=k: (E.log.append(('alloc', k)), E.fake_struct())[1])
        for f, k in PARSEF.items():
            E.stub(f, lambda E, k=k: E.log.append(('parse', k, E.sid.get(E.r(4)))))
        for f, k in FREEF.items():
            E.stub(f, lambda E, k=k: E.log.append(('free', k, E.sid.get(E.r(3)))))
        for f, k in DESTF.items():
            E.stub(f, lambda E, k=k: E.log.append(('destroy', k, E.sid.get(E.r(3)), E.r(4))))
        mgr = E.call(0x02EA5848, 0)
        E.mgr = mgr
        E.eq = E.w(mgr + 0x2574)
        etc = E.alloc(0x400, b'\0')                          # fighter_param_etc +0x234: effect table data
        E.setw(mgr + 0xDA0 + 0x234, etc)
        E.call(0x02EA5BC0, mgr)
        return mgr
    setup(P)
    setup(O)
    check('constructor: manager / equipment object sizes', (P.sizes[:1], P.memsets),
          ([info['mgr_size']], [0x320 + 4 * cap]))
    check('  (unpatched: 0x25B0 / 0x424)', (O.sizes[:1], O.memsets), ([0x25B0], [0x424]))
    check('equipment object pointer stored', (P.eq != 0, P.w(0x10353FC0) == P.eq), (True, True))
    NEWL = {n: v[1] for n, v in lay.items()}
    OLDL = {n: v[0] for n, v in lay.items()}

    def arr(E, L, name, k, size=4):
        return E.w(E.mgr + L[name] + size * k)
    check('loader: refcounts / x1324 / x1428 / x152C cleared, kinds 0x00-0x%X' % (cap - 1),
          [k for k in range(cap) for n in ('refcnt', 'x1324', 'x1428', 'x152C') if arr(P, NEWL, n, k)], [])
    check('loader: kind -> fighter_param entry, kinds 0x00-0x40 = unpatched',
          [k for k in range(K.OLD_N) if arr(P, NEWL, 'fpidx', k) != arr(O, OLDL, 'fpidx', k)], [])
    for r in kinds:
        check('loader: kind 0x%X -> its fighter_param entry' % r['kind'], arr(P, NEWL, 'fpidx', r['kind']),
              entries_order.index(r['kind']))
    check('loader: the old arrays (dead now) untouched', {arr(P, OLDL, n, k) for n in ('refcnt', 'fpidx') for k in
                                                          range(K.OLD_N)}, {0xA5A5A5A5})

    VLL, VLU = K.VL_LOAD, K.VL_UNLOAD

    def state(E, L, k):
        vl = arr(E, L, 'vl', k)
        att = E.mgr + L['att'] + 0x24 * k
        attv = [E.w(att + 4 * i) for i in range(9)]
        attp = [E.w(E.mgr + L['attp'] + 8 * k), E.w(E.mgr + L['attp'] + 8 * k + 4)]
        return {'vl': E.sid.get(vl, vl), 'refcnt': arr(E, L, 'refcnt', k), 'eq': E.sid.get(E.w(E.eq + 0x320 + 4 * k)),
                'vl50': (arr(E, L, 'vl50', k) - vl) if vl else arr(E, L, 'vl50', k),
                # fake-struct words are (id << 16) | offset: as ('field', offset) of this kind's struct
                'att': [('field', v & 0xFFFF) if vl and v >> 16 == E.sid.get(vl) else v for v in attv],
                'attp': [attp[0] - att if attp[0] else 0, attp[1]],
                'x': [arr(E, L, n, k) for n in ('x1324', 'x1428', 'x152C')]}
    diffs, mirror = [], []
    for k in range(K.OLD_N):
        seq = []
        for E, L in ((P, NEWL), (O, OLDL)):
            E.log = []
            st = []
            E.call(VLL, E.mgr, k)
            st.append(state(E, L, k))
            E.call(VLL, E.mgr, k)
            st.append(state(E, L, k))
            E.call(VLU, E.mgr, k)
            st.append(state(E, L, k))
            if E is P:
                mirror.append(arr(P, OLDL, 'vl', k) == arr(P, NEWL, 'vl', k))
            E.call(VLU, E.mgr, k)
            st.append(state(E, L, k))
            if E is P:
                mirror.append(arr(P, OLDL, 'vl', k) == arr(P, NEWL, 'vl', k) == 0)
            seq.append((E.log, st))
        if seq[0] != seq[1]:
            diffs.append((hex(k), seq[0], seq[1]))
    check('vl load x2 / unload x2 of every kind 0x00-0x40: calls, files and arrays = unpatched', diffs[:1], [])
    check('  old vl array mirrors the new one (loaded, then cleared)', all(mirror), True)
    for r in kinds:
        k, b = r['kind'], r['bkind']
        P.log = []
        P.call(VLL, P.mgr, k)
        fn = 'param/fighter/%s.bin' % r['vl']
        base_file = 'param/fighter/%s.bin' % img.cstr(img.w(K.TABLES['vl'][0] + 4 * b))
        log = P.log
        check('vl load 0x%X: loads %s\'s params, then its own file with %s\'s parser' % (k, info['names'][b], info['names'][b]),
              [x[:2] for x in log], [('alloc', b), ('file', base_file), ('parse', b), ('alloc', b), ('file', fn), ('parse', b)])
        sk = state(P, NEWL, k)
        sb = state(P, NEWL, b)
        check('  its struct in new vl / equipment field / vl50 / refcount', (sk['vl'], sk['eq'], sk['vl50'], sk['refcnt']),
              (log[5][2], log[5][2], 0x50, 1))
        check('  att / attp records (as the base\'s, from its own struct)', (sk['att'], sk['attp']), (sb['att'], [0, 3]))
        check('  (and they are filled)', sum(isinstance(v, tuple) for v in sk['att']), 4)
        check('  the base loaded once, mirrored', (sb['refcnt'], sb['vl'], arr(P, OLDL, 'vl', b) == arr(P, NEWL, 'vl', b)),
              (1, log[2][2], True))
        check('  no write into the old arrays at kind 0x%X (old refcnt[0] at 0x111C + 4 * 0x41)' % k,
              arr(P, OLDL, 'vl', k), 0xA5A5A5A5 if k == 0x41 else arr(P, OLDL, 'vl', k))
        P.log = []
        P.call(VLL, P.mgr, k)
        P.call(VLL, P.mgr, b)
        check('  loaded again (2) and the base by a player: no new loads', (P.log, state(P, NEWL, k)['refcnt'],
                                                                           state(P, NEWL, b)['refcnt']), ([], 2, 2))
        P.call(VLU, P.mgr, k)
        check('  unload: still loaded', (P.log, state(P, NEWL, k)['refcnt']), ([], 1))
        P.call(VLU, P.mgr, k)
        sk = state(P, NEWL, k)
        check('  unload: its struct freed with %s\'s functions, fields cleared, the base released (not freed)' % info['names'][b],
              ([x[:3] for x in P.log], sk['vl'], sk['eq'], sk['refcnt'], state(P, NEWL, b)['refcnt']),
              ([('free', b, log[5][2]), ('destroy', b, log[5][2])], 0, None, 0, 1))
        P.log = []
        P.call(VLU, P.mgr, b)
        check('  the base unloaded by its player: freed, both vl arrays cleared',
              ([x[:3] for x in P.log], arr(P, NEWL, 'vl', b), arr(P, OLDL, 'vl', b)),
              ([('free', b, log[2][2]), ('destroy', b, log[2][2])], 0, 0))
        P.log = []
        P.call(VLL, P.mgr, k)
        P.call(0x02EA6B6C, P.mgr)                       # unload all (0..capacity-1, once each)
        check('  unload-all reaches kind 0x%X: it and its base freed' % k,
              (sorted(x[0] for x in P.log if x[0] in ('free', 'destroy')), state(P, NEWL, k)['refcnt'],
               state(P, NEWL, b)['refcnt']), (['destroy', 'destroy', 'free', 'free'], 0, 0))

    # motion table: 0x02EA9064(mgr, kind) builds descriptor +0x1C from vl group 1 into the kind's own table
    print('# motion table')
    for r in kinds:
        k, b = r['kind'], r['bkind']
        n = r['mcount']
        for E, kk in ((P, k), (P, b), (O, b)):
            g = E.alloc(6 * n, b'\0')
            for i in range(n):
                E.mu.mem_write(g + 6 * i, bytes([i & 1, (i * 7 + kk) & 0xFF]))
            vs = E.alloc(0x20, b'\0')
            E.setw(vs + 0xC, g)
            E.setw(E.mgr + (NEWL if E is P else OLDL)['vl'] + 4 * kk, vs)
        base_tbl = O.w(O.w(O.call(desc_fn, 0, b) + 4))
        before = bytes(P.mu.mem_read(base_tbl, 8 * n))
        t = P.call(0x02EA9064, P.mgr, k)
        check('0x02EA9064(0x%X) = its own table (descriptor +0x1C)' % k, (t, P.w(r['desc'] + 0x1C)), (r['mtable'], r['mtable']))
        check('  the base\'s table untouched', bytes(P.mu.mem_read(base_tbl, 8 * n)), before)
        got = [P.mu.mem_read(t + 8 * i + 4, 1)[0] for i in range(n)]
        check('  its table holds its vl group 1', got, [(i * 7 + k) & 0xFF for i in range(n)])
        tb, tbo = P.call(0x02EA9064, P.mgr, b), O.call(0x02EA9064, O.mgr, b)
        check('  the base\'s table built as unpatched', bytes(P.mu.mem_read(tb, 8 * n)), bytes(O.mu.mem_read(tbo, 8 * n)))

    # ------------------------------------------------------------ AI guard
    print('# AI amiibo learning guard')

    def ai_run(E, kind, flag):
        rec_area = E.alloc(0x488 * 3, b'\0')
        r31, r30 = E.alloc(0x100, b'\0'), E.alloc(0x100, b'\0')
        E.mu.mem_write(r31 + 0x4B, bytes([flag]))
        E.setw(r30 + 0x1C, 0x23A)
        E.mu.reg_write(REGS[31], r31)
        E.mu.reg_write(REGS[30], r30)
        E.mu.reg_write(REGS[29], rec_area - 0x290)
        E.mu.reg_write(REGS[28], 0x488)
        E.mu.reg_write(REGS[10], kind)
        E.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
        E.mu.emu_start(0x02751AF0, 0x02752098, count=100)
        data = bytes(E.mu.mem_read(rec_area, 0x488 * 3))
        return E.mu.reg_read(UC_PPC_REG_PC), [(o, v) for o, v in
                                              ((o, struct.unpack('>I', data[o:o + 4])[0]) for o in range(0, len(data), 4)) if v]
    diff = [(k, f) for k in range(K.OLD_N) for f in (0, 1) if ai_run(P, k, f) != ai_run(O, k, f)]
    check('both increments, kinds 0x00-0x40 = unpatched', diff, [])
    check('kind 3: rec+0x384+12 / rec+0x280+12 incremented', (ai_run(P, 3, 1)[1], ai_run(P, 3, 0)[1]),
          ([(0x488 + 0x384 + 12, 1)], [(0x488 + 0x280 + 12, 1)]))
    for k in (0x41, cap - 1):
        check('kind 0x%X: nothing written (unpatched: %r)' % (k, (ai_run(O, k, 1)[1], ai_run(O, k, 0)[1]) if k == 0x41 else '-'),
              (ai_run(P, k, 1)[1], ai_run(P, k, 0)[1]), ([], []))

    print('FAILS', fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
