#!/usr/bin/env python3
"""Runs tools/edge_counter_cave.py's code in unicorn, in a patched RPX, against Marth's own counter code.

  python3 tools/edge_counter_cave_test.py [BASE.rpx [PATCHED.rpx]]

BASE defaults to build/cross_f.rpx; PATCHED (BASE + the cave's arguments, and maybe other caves) is made
in a temporary folder when not given. Fake fighters / modules in emulator memory; the game functions
the cave calls are stubbed (recording their arguments), everything else is the game's code.

Checks:
- words: the patched RPX has every word; the hooks' words in BASE are the game's (or the cave's own),
  no relocation on them, the cave space is free in BASE;
- setup (Zelda's slot 0, entered at its first word): kind 0x42 builds shield group 1 through the
  game's group init 0x0200C858 -> 0x02C6F5C0, with exactly the arguments Marth's setup (0x02F1E468,
  run on the same kind of fake module) gives the generic init 0x02C6F38C (group struct, module fields,
  group 1, first free shape, one shape) and the same group bytes; the shape is Marth's layout (his
  vl x / y / z / radius / bone land where ours put p1 / p2 / radius / bone) with Ultimate's values;
  the module's shape count grows; 0x0200BD8C switches the new shape off; then Zelda's own slot 0 runs
  (her setup with r5 = 1, the fighter in r4), the non-volatile registers and the stack are kept;
  Zelda's kind (0x10) and kind 0x42 without a shield module: nothing built, Zelda's code as before;
- slot 42 (0x02F982F8): kind 0x42, group 1, status 0x155, first hit: float 0x01000006 = the damage,
  0x01000007 = the side 0x02C22684 returns (called with Marth's arguments), flag 0x21000010 on,
  0x21000011 only for a non-fighter attacker (category 1 / 2 / 3), the other flags / floats untouched;
  hit data +0x4F == 6: the side from the positions (+1.0 / -1.0 as Marth's), and 0x02C22684's when the
  attacker is gone; nothing for: a second hit, group 0, another status, an uncounterable hit (+0x54),
  Zelda's kind; registers kept;
- slot 43 (0x02F982FC): 0 and message +8 |= 1 for kind 0x42 in 0x155 with 0x21000010 on; 1 and the
  message untouched without the flag, in another status, or for Zelda's kind.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edge_counter_cave as C  # noqa: E402
import kind_expand as K  # noqa: E402
from kind_expand_test import Emu, REGS  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_MSR,  # noqa: E402
                               UC_PPC_REG_FPR1, UC_PPC_REG_FPR2)

RPX = os.path.join(HERE, '..', 'build', 'cross_f.rpx')
MARTH_SETUP = 0x02F1E468
GENERIC_INIT = 0x02C6F38C
ZELDA_SETUP = 0x02F976C4
PARAM_MGR = 0x102FF448           # [0x10300000 - 0xBB8]: FighterParamManager
ZELDA = 0x10

fails = 0


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


def f2d(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def d2f(q):
    return struct.unpack('>d', struct.pack('>Q', q))[0]


def fbits(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


class Run(Emu):
    def __init__(self, path):
        super().__init__(path)
        self.calls = []
        self.side = -1.0             # what the 0x02C22684 stub returns
        self.gone = 0                # 0x02BEF50C
        self.attacker_x = 0.0
        self.hitdata = 0
        self.pos = self.alloc(0x10)
        self.handle_obj = self.alloc(0x40)
        self.stub(GENERIC_INIT, self.generic_init)
        self.stub(ZELDA_SETUP, lambda e: e.rec('zelda_setup', 4, 5))
        self.stub(C.SIDE, self.side_fn)
        self.stub(C.HANDLE, self.handle_fn)
        self.stub(C.HANDLE_GONE, lambda e: (e.rec('gone', 3), e.gone)[1])
        self.stub(C.HANDLE_POS, self.pos_fn)
        self.am_fn = self.alloc(4)          # the attacker AttackModule's vt +0x194
        self.stub(self.am_fn, lambda e: (e.rec('hitdata', 3, 4, 5), e.hitdata)[1])

    def rec(self, name, *regs):
        self.calls.append((name,) + tuple(self.r(i) for i in regs))

    def generic_init(self, e):
        regs = tuple(self.r(i) for i in range(3, 11))
        shape = bytes(self.mu.mem_read(regs[4], 0x20))
        grp = bytes(self.mu.mem_read(regs[0], 0x34))
        self.calls.append(('init', regs, shape, grp))
        self.setw(regs[0], regs[6])                                   # what 0x02C6F38C does to it
        self.mu.mem_write(regs[0] + 4, struct.pack('>hh', regs[7], regs[5]))
        return regs[5]

    def side_fn(self, e):
        f1 = d2f(self.mu.reg_read(UC_PPC_REG_FPR1))
        f2 = d2f(self.mu.reg_read(UC_PPC_REG_FPR2))
        self.calls.append(('side',) + tuple(self.r(i) for i in range(3, 8)) + (round(f1, 4), round(f2, 4)))
        self.mu.reg_write(UC_PPC_REG_FPR1, f2d(self.side))

    def handle_fn(self, e):
        self.rec('handle', 3, 4, 5, 6)
        self.setw(self.r(4), self.handle_obj)
        self.setw(self.r(4) + 4, 0)

    def pos_fn(self, e):
        self.rec('pos', 3)
        self.mu.mem_write(self.pos, struct.pack('>f', self.attacker_x))
        return self.pos

    def run(self, fn, *args):
        self.calls = []
        for i in range(14, 32):
            self.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # FP on
        r = self.call(fn, *args)
        kept = all(self.r(i) == 0x5A5A0000 + i for i in range(14, 32))
        return r, kept and self.mu.reg_read(UC_PPC_REG_1) == 0x700F0000 + 0x0

    def fighter(self, kind, status=C.STATUS, shield=True):
        """a fake fighter: {fighter, acc, M (kind-2 ShieldModule), work (status work: floats, flags)}"""
        f = self.alloc(0x80, b'\0')
        acc = self.alloc(0x7400, b'\0')
        self.setw(f + C.KIND_AT, kind)
        self.setw(f + C.ACC, acc)
        st = self.alloc(0x80, b'\0')
        self.setw(acc + C.STATUS_MOD, st)
        self.setw(st + 0x48, status)
        self.setw(st + 0x44, self.alloc(0x800, b'\0'))             # Zelda's slot 0 writes her native statuses here
        wm = self.alloc(0x20, b'\0')
        cats = self.alloc(0x40, b'\0')
        inst = self.alloc(0x20, b'\0')
        sw = self.alloc(0x20, b'\0')
        floats = self.alloc(0x40)
        flags = self.alloc(0x10)
        ints = self.alloc(0x400, b'\0')
        self.setw(wm + 8, cats)
        self.setw(cats, inst)
        self.setw(cats + 4, sw)
        self.setw(inst + 0xC, ints)
        self.setw(sw + 4, floats)
        self.setw(sw + 0x14, flags)
        self.setw(acc + C.WORK, wm)
        for i in range(16):
            self.setw(floats + 4 * i, fbits(100.0 + i))
        self.setw(flags, 0x0000C00F)
        self.setw(flags + 4, 0x12345678)
        posture = self.alloc(0x40, b'\0')
        self.setw(acc + C.POSTURE, posture)
        self.setw(acc + C.SIDE_MOD, 0x7290AAAA)
        m = 0
        if shield:
            m = self.alloc(0x50, b'\0')
            groups = self.alloc(5 * 0x34, b'\0')
            shapes = self.alloc(5 * 0x24, b'\0')
            self.setw(m + 8, groups)
            self.setw(m + 0xC + 4, shapes)                 # M+0xC: {.., shapes} (0x02C6F954 reads +4)
            self.setw(m + 0x14, 1)                         # the guard's shape taken
            self.setw(m + 0x44, 0x4444)
            self.setw(m + 0x28, 1)                         # groups on so far: the guard's
            for i in range(5):
                self.setw(shapes + 0x24 * i + 0x20, 0xFFFFFFFF)
            self.setw(acc + C.SHIELD, m)
        return dict(f=f, acc=acc, m=m, floats=floats, flags=flags, ints=ints, posture=posture, st=st)

    def floats(self, fk):
        return [round(struct.unpack('>f', bytes(self.mu.mem_read(fk['floats'] + 4 * i, 4)))[0], 4) for i in range(16)]

    def flagw(self, fk):
        return self.w(fk['flags']), self.w(fk['flags'] + 4)


def words_checks(base, patched):
    p = C.patches()
    img, pimg = K.Image(base), K.Image(patched)
    check('the patched RPX has every word', [hex(a) for a, w in sorted(p.items()) if pimg.w(a) != w][:4], [])
    check('the hooks\' words in the base are the game\'s (or the cave\'s)',
          [hex(a) for a, w in C.ORIGINAL.items() if img.w(a) not in (w, p[a])], [])
    check('no relocation on a hooked word', [hex(a) for a in C.ORIGINAL if a in img.relocs()], [])
    check('the cave space is free in the base', [hex(a) for a in range(C.CAVE, C.LIMIT, 4)
                                                 if C.word_or_0(img, a) not in (0, p.get(a, 0))][:4], [])
    vt = 0x10147F34
    check('Zelda\'s vtable slots 0 / 42 / 43 point at the hooked words',
          [img.w(vt + 0xC + 8 * s) for s in (0, 42, 43)], [C.SETUP_HOOK, C.SLOT42_HOOK, C.SLOT43_HOOK])


def setup_checks(e, kind):
    # Marth's setup on a fake Marth (his vl block: x 1.5, y 2.5, z 3.5, radius 4.5, bone 7)
    mk = e.fighter(0x12)
    vl = e.alloc(0x200, b'\0')
    block = e.alloc(0x400, b'\0')
    mgr = e.alloc(0x2000, b'\0')
    e.setw(PARAM_MGR, mgr)
    e.setw(mgr + 0x1164, vl)
    e.setw(vl + 0x138, block)
    e.setw(mk['ints'] + 0x12C, 2)                                  # his custom slot: block + 2 * 0x3C
    b = block + 2 * 0x3C
    e.setw(b + 0x24, 7)
    for o, v in ((0x28, 1.5), (0x2C, 2.5), (0x30, 3.5), (0x34, 4.5)):
        e.setw(b + o, fbits(v))
    e.calls = []
    e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    e.call(MARTH_SETUP, 0, mk['f'], 1)
    marth = [c for c in e.calls if c[0] == 'init']
    check('Marth\'s setup: one group init', len(marth), 1)
    mm = mk['m']

    sk = e.fighter(kind)
    m = sk['m']
    r, kept = e.run(C.SETUP_HOOK, 0x5BEC0000, sk['f'], 0x77)
    inits = [c for c in e.calls if c[0] == 'init']
    check('kind 0x%X: one group init' % kind, len(inits), 1)
    if inits and marth:
        def rel(c, mod):
            g = e.w(mod + 8)
            r3, r4, r5, r6, r7, r8, r9, r10 = c[1]
            return (r3 - g, r4 - mod, r5, r6 - mod, r8, r9, r10)
        check('group init arguments as Marth\'s (group struct, M+0x18, [M+0x44], M+0xC, count, group, '
              'first shape)', rel(inits[0], m), rel(marth[0], mm))
        check('  = group 1 at [M+8]+0x34, one shape, the first free one', rel(inits[0], m),
              (0x34, 0x18, 0x4444, 0xC, 1, 1, 1))
        check('group bytes +0x28..+0x2C as Marth\'s', inits[0][3][0x28:0x2D], marth[0][3][0x28:0x2D])
        ms = struct.unpack('>7fHB', marth[0][2][:0x1F])
        check('Marth\'s shape layout: x y z x y z radius bone type', ms, (1.5, 2.5, 3.5, 1.5, 2.5, 3.5, 4.5, 7, 2))
        ours = struct.unpack('>7fHB', inits[0][2][:0x1F])
        want = tuple(round(v, 4) for v in C.SHAPE['p1'] + C.SHAPE['p2'] + (C.SHAPE['radius'],)) + (C.SHAPE['bone'], 2)
        check('our shape: (0, 2, 8.3) - (0, 20, 8.3), radius 6, joint 0, capsule',
              tuple(round(v, 4) for v in ours[:7]) + ours[7:], want)
    check('the module\'s shape count grows by one', e.w(m + 0x14), 2)
    shapes = e.w(m + 0xC + 4)
    check('the new shape (index 1) switched off, the guard\'s untouched',
          (e.w(shapes + 0x24 + 0x20), e.w(shapes + 0x20)), (0, 0xFFFFFFFF))
    check('groups on: unchanged (1)', e.w(m + 0x28), 1)
    check('then Zelda\'s setup (fighter, create)', [c for c in e.calls if c[0] == 'zelda_setup'],
          [('zelda_setup', sk['f'], 1)])
    check('registers and stack kept, back at the caller', kept, True)
    check('Marth\'s module: count grown too (his setup adds its result)', e.w(mm + 0x14), 2)

    for what, fk in (('Zelda (0x10)', e.fighter(ZELDA)), ('kind 0x%X without a shield module' % kind,
                                                          e.fighter(kind, shield=False))):
        r, kept = e.run(C.SETUP_HOOK, 0, fk['f'], 0)
        check('%s: no group built, Zelda\'s setup runs' % what, [c[0] for c in e.calls], ['zelda_setup'])
        if fk['m']:
            check('%s: module untouched' % what, (e.w(fk['m'] + 0x14), e.w(fk['m'] + 0x28)), (1, 1))
        check('%s: registers kept' % what, kept, True)


def message(e, fk, damage=13.5, group=1, category=0, hid=3, part=1, f18=0.25, f1c=-0.75):
    am = e.alloc(0x10, b'\0')
    vt = e.alloc(0x200, b'\0')
    e.setw(am, vt)
    e.setw(vt + 0x194, e.am_fn)
    rec = e.alloc(0x40, b'\0')
    e.setw(rec + 0x18, (category << 28) | 0x00120034)
    e.mu.mem_write(rec + 0x1C, bytes([category]))
    e.mu.mem_write(rec + 0x26, bytes([hid]))
    e.mu.mem_write(rec + 0x29, bytes([part]))
    msg = e.alloc(0x40, b'\0')
    e.setw(msg + 8, am)
    e.setw(msg + 0xC, fbits(damage))
    e.setw(msg + 0x10, rec)
    e.setw(msg + 0x14, group)
    e.setw(msg + 0x18, fbits(f18))
    e.setw(msg + 0x1C, fbits(f1c))
    return msg, am, rec


def hitdata(e, b4f=0, b54=0):
    h = e.alloc(0x68, b'\0')
    e.mu.mem_write(h + 0x4F, bytes([b4f]))
    e.mu.mem_write(h + 0x54, bytes([b54]))
    e.hitdata = h
    return h


def slot42_checks(e, kind):
    base_floats = [round(100.0 + i, 4) for i in range(16)]
    for cat, label in ((0, 'fighter'), (1, 'weapon'), (2, 'item'), (3, 'stage')):
        fk = e.fighter(kind)
        msg, am, rec = message(e, fk, category=cat)
        hd = hitdata(e)
        e.side = -1.0
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        fl = e.floats(fk)
        want = list(base_floats)
        want[6], want[7] = 13.5, -1.0
        check('slot 42, %s attacker: float 6 = damage, float 7 = the side, others untouched' % label, fl, want)
        check('slot 42, %s attacker: flag 0x21000010 on%s' % (label, ', 0x21000011 on' if cat else ''),
              e.flagw(fk), (0x0000C00F | 0x10000 | (0x20000 if cat else 0), 0x12345678))
        if cat == 0:
            check('slot 42: hit data asked with (AM, hitbox id, part)', [c for c in e.calls if c[0] == 'hitdata'],
                  [('hitdata', am, 3, 1)])
            check('slot 42: 0x02C22684 with Marth\'s arguments', [c for c in e.calls if c[0] == 'side'],
                  [('side', 0x7290AAAA, am, hd, 3, 1, 0.25, -0.75)])
            check('slot 42: no handle without +0x4F == 6', [c[0] for c in e.calls], ['hitdata', 'side'])
        check('slot 42 (%s): registers kept' % label, kept, True)

    # second hit: nothing
    fk = e.fighter(kind)
    e.setw(fk['flags'], 0x0000C00F | 0x10000)
    msg, am, rec = message(e, fk, damage=40.0, category=1)
    hitdata(e)
    e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    check('slot 42, second hit: nothing written, nothing called',
          (e.floats(fk), e.flagw(fk), e.calls), (base_floats, (0x0000C00F | 0x10000, 0x12345678), []))

    for what, fk, kw, hd in (('group 0 (the guard)', e.fighter(kind), {'group': 0}, {}),
                             ('status 0x15B', e.fighter(kind, status=0x15B), {}, {}),
                             ('Zelda (0x10)', e.fighter(ZELDA), {}, {}),
                             ('uncounterable (+0x54)', e.fighter(kind), {}, {'b54': 1})):
        msg, am, rec = message(e, fk, **kw)
        hitdata(e, **hd)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('slot 42, %s: nothing written' % what, (e.floats(fk), e.flagw(fk)), (base_floats, (0x0000C00F, 0x12345678)))
        check('slot 42, %s: registers kept' % what, kept, True)

    # hit data +0x4F == 6: the side from the positions
    for my_x, att_x, gone, want_side in ((0.0, 10.0, 0, 1.0), (10.0, 0.0, 0, -1.0), (5.0, 5.0, 0, -1.0),
                                         (0.0, 10.0, 1, -0.5)):
        fk = e.fighter(kind)
        e.setw(fk['posture'] + 0x10, fbits(my_x))
        e.attacker_x, e.gone, e.side = att_x, gone, -0.5
        msg, am, rec = message(e, fk, category=1)
        hitdata(e, b4f=6)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('slot 42, +0x4F == 6, him at %g, attacker at %g%s: side %g' % (my_x, att_x, ' (gone)' if gone else '',
                                                                           want_side), e.floats(fk)[7], want_side)
        hc = [c for c in e.calls if c[0] == 'handle']
        check('  the attacker\'s handle from its id', [c[3:] for c in hc], [(rec_id(e, rec), 0)])
        check('  registers kept', kept, True)
    e.gone = 0


def rec_id(e, rec):
    return e.w(rec + 0x18)


def slot43_checks(e, kind):
    for what, fk, flag, want in (('flag on', e.fighter(kind), True, 0),
                                 ('flag off', e.fighter(kind), False, 1),
                                 ('status 0x15B, flag on', e.fighter(kind, status=0x15B), True, 1),
                                 ('Zelda, flag on', e.fighter(ZELDA), True, 1)):
        if flag:
            e.setw(fk['flags'], 0x0000C00F | 0x10000)
        msg = e.alloc(0x20, b'\0')
        e.mu.mem_write(msg + 8, bytes([0x40]))
        r, kept = e.run(C.SLOT43_HOOK, 0, fk['f'], msg)
        check('slot 43, %s: returns %d' % (what, want), r, want)
        check('slot 43, %s: message +8 %s' % (what, '|= 1' if want == 0 else 'untouched'),
              bytes(e.mu.mem_read(msg + 8, 1))[0], 0x41 if want == 0 else 0x40)
        check('slot 43, %s: registers kept' % what, kept, True)


def main():
    a = sys.argv[1:]
    base = a[0] if a else RPX
    tmp = None
    if len(a) > 1:
        patched = a[1]
    else:
        tmp = tempfile.TemporaryDirectory()
        patched = os.path.join(tmp.name, 'cross_f.rpx')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), base, patched] + C.args(),
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
    kind = C.kind()
    check('Sephiroth\'s kind from extra_kinds.json', kind, 0x42)
    words_checks(base, patched)
    e = Run(patched)
    setup_checks(e, kind)
    slot42_checks(e, kind)
    slot43_checks(e, kind)
    print('%d failure(s)' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
