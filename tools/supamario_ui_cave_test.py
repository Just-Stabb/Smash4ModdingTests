#!/usr/bin/env python3
"""Runs tools/supamario_ui_cave.py's code in unicorn, in a patched RPX (Supamario's Ultra Instinct: the counter shape,
the counter's record and the autododge).

  python3 tools/supamario_ui_cave_test.py BASE.rpx [PATCHED.rpx]

BASE: exe_v46z_outline4 (the cave's base); PATCHED (BASE + the cave's arguments) is made in a temporary folder when not
given. Fake fighters / modules / a fighter table in emulator memory; the game functions the cave calls are stubbed
(recording their arguments), Marth's setup and the group init's wrapper are the game's code.

Checks:
- words: the patched RPX has every word, the hooks' words in BASE are the game's, no relocation on them, Mario's vtable
  slots 0 / 42 / 43 point at the hooked words, the cave space is free in BASE;
- setup (Mario's slot 0, entered at its first word): kind 0x41 builds shield group 1 through 0x0200C858 -> 0x02C6F5C0
  with the arguments Marth's setup (0x02F1E468, the same kind of fake module) gives the generic init 0x02C6F38C (group
  struct, module fields, group 1, the first free shape, one shape) and the same group bytes; the shape's layout is
  Marth's (x y z x y z radius bone type) with the capsule's values; the shape switched off (0x0200BD8C); then Mario's
  setup (0x02F1A598) with r5 = 1 and the fighter; non-volatile registers and the stack kept. Mario (kind 3), another kind
  and kind 0x41 without a shield module: nothing built, Mario's setup with r5 = 1 as before;
- slot 42: kind 0x41, group 1, status 0x157, first hit: float 6 = the damage, 7 = the side, 8 / 9 = the X / Y of the
  fighter to answer, flags 0x21000010 (+ 0x21000011 not a fighter, + 0x21000012 found); a fighter attacker: its own place
  (left / right); a weapon: its current owner's place (owner module +0x34), the side from the owner; an item the same; a
  weapon whose owner is no fighter (a gimmick's id) or gone: no target, the side from the weapon's place; a stage gimmick
  (category 3) whose object is gone: Marth's side function's value; nothing for: a second hit, group 0, another status,
  an uncounterable hit (+0x54), Mario's kind (3); registers kept;
- slot 43: 0x157 -> 0 and the handled bit whatever else; transformed (TIMER_0 > 1500) in Wait / Walk / WalkBrake /
  Squat .. SquatRv with a fighter's hit records holding him -> 0, the handled bit, TIMER_1 (attacker right) or TIMER_2
  (left) = 4.0 and the other 0 through set_float, the hit data asked with (AM, node +0x27, part); the record found in a
  later part / after other nodes / of the second live fighter; -> 1 and nothing written for: no fighter's records (a
  weapon / item / gimmick hit), records of a dead fighter, his own records, records off (+0x4C 0), not transformed
  (TIMER_0 1000 / 0), another status (Dash 3, Fall 0xE, Damage 0x45, Guard 0x1C, the dodge 0x158), an uncounterable
  hit (+0x54), Mario (kind 3) in Wait with a fighter's records holding him; registers kept.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import supamario_ui_cave as C  # noqa: E402
import kind_expand as K  # noqa: E402
from kind_expand_test import Emu, REGS  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_MSR,  # noqa: E402
                               UC_PPC_REG_FPR1, UC_PPC_REG_FPR2)

MARTH_SETUP = 0x02F1E468
GENERIC_INIT = 0x02C6F38C
PARAM_MGR = 0x102FF448
MARIO = 0x3

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


def bitsf(w):
    return struct.unpack('>f', struct.pack('>I', w))[0]


class Run(Emu):
    def __init__(self, path):
        super().__init__(path)
        self.calls = []
        self.side = -0.5                 # what the 0x02C22684 stub returns
        self.objects = {}                # id -> {'entry', 'pos', 'alive'}
        self.hitdata = 0
        self.vars = {}                   # his WorkModule's user variables (get / set_float stubs)
        self.stub(GENERIC_INIT, self.generic_init)
        self.stub(C.SETUP_BODY, lambda e: e.rec('mario_setup', 4, 5))
        self.stub(C.SIDE, self.side_fn)
        self.stub(C.HANDLE, self.handle_fn)
        self.stub(C.HANDLE_GONE, self.gone_fn)
        self.stub(C.HANDLE_POS, self.pos_fn)
        self.am_fn = self.alloc(4)
        self.stub(self.am_fn, lambda e: (e.rec('hitdata', 3, 4, 5), e.hitdata)[1])
        self.get_fn = self.alloc(4)
        self.stub(self.get_fn, self.get_float)
        self.set_fn = self.alloc(4)
        self.stub(self.set_fn, self.set_float)
        self.wm_vt = self.alloc(0x100, b'\0')
        self.setw(self.wm_vt + 0x44, self.get_fn)
        self.setw(self.wm_vt + 0x4C, self.set_fn)
        self.post_fn = self.alloc(4)
        self.stub(self.post_fn, self.posture_pos)
        self.post_vt = self.alloc(0x100, b'\0')
        self.setw(self.post_vt + 0x44, self.post_fn)
        self.table = self.alloc(0x10, b'\0')
        self.setw(C.FIGHTERS, self.table)
        self.ftab = self.alloc(0x10, b'\0')
        self.setw(self.table, self.ftab)
        self.entries = self.alloc(4 * C.FIGHTER_ENTRY, b'\0')
        self.setw(self.ftab, self.entries)
        self.setw(self.ftab + 8, 0)
        self.mgr = self.alloc(0x10, b'\0')
        self.setw(C.OBJ_MANAGER, self.mgr)

    def rec(self, name, *regs):
        self.calls.append((name,) + tuple(self.r(i) for i in regs))

    def generic_init(self, e):
        regs = tuple(self.r(i) for i in range(3, 11))
        shape = bytes(self.mu.mem_read(regs[4], 0x20))
        grp = bytes(self.mu.mem_read(regs[0], 0x34))
        self.calls.append(('init', regs, shape, grp))
        self.setw(regs[0], regs[6])
        self.mu.mem_write(regs[0] + 4, struct.pack('>hh', regs[7], regs[5]))
        return regs[5]

    def side_fn(self, e):
        f1 = d2f(self.mu.reg_read(UC_PPC_REG_FPR1))
        f2 = d2f(self.mu.reg_read(UC_PPC_REG_FPR2))
        self.calls.append(('side',) + tuple(self.r(i) for i in range(3, 8)) + (round(f1, 4), round(f2, 4)))
        self.mu.reg_write(UC_PPC_REG_FPR1, f2d(self.side))

    def handle_fn(self, e):
        self.rec('handle', 3, 4, 5, 6)
        o = self.objects.get(self.r(5))
        self.setw(self.r(4), o['entry'] if o else 0)
        self.setw(self.r(4) + 4, self.r(5))

    def gone_fn(self, e):
        idw = self.w(self.r(3) + 4)
        o = self.objects.get(idw)
        self.calls.append(('gone', idw))
        return 0 if o and o['alive'] else 1

    def pos_fn(self, e):
        idw = self.w(self.r(3) + 4)
        self.calls.append(('pos', idw))
        return self.objects[idw]['pos']

    def get_float(self, e):
        v = self.vars.get(self.r(4), 0.0)
        self.calls.append(('get', self.r(3), self.r(4)))
        self.mu.reg_write(UC_PPC_REG_FPR1, f2d(v))

    def set_float(self, e):
        v = round(d2f(self.mu.reg_read(UC_PPC_REG_FPR1)), 4)
        self.calls.append(('set', self.r(3), self.r(4), v))
        self.vars[self.r(4)] = v

    def posture_pos(self, e):
        p = self.r(3)
        self.calls.append(('posture', p))
        return p + 0x20

    def run(self, fn, *args):
        self.calls = []
        for i in range(14, 32):
            self.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        r = self.call(fn, *args)
        kept = all(self.r(i) == 0x5A5A0000 + i for i in range(14, 32))
        return r, kept and self.mu.reg_read(UC_PPC_REG_1) == 0x700F0000

    # ---- objects
    def obj(self, oid, x=0.0, y=0.0, alive=True, owner=None):
        """a weapon / item / gimmick object: its entry (+0xC its accessor: +0x6C the owner module)"""
        entry = self.alloc(0x40, b'\0')
        acc = self.alloc(0x80, b'\0')
        self.setw(entry, oid)
        self.setw(entry + 0xC, acc)
        if owner is not None:
            om = self.alloc(0x40, b'\0')
            self.setw(acc + C.BASE_OWNER, om)
            self.setw(om + 0x34, owner)
        pos = self.alloc(0x10, b'\0')
        self.setw(pos, fbits(x))
        self.setw(pos + 4, fbits(y))
        self.objects[oid] = dict(entry=entry, pos=pos, alive=alive)
        return entry

    def fighter(self, kind, status=C.ST_UI, shield=True, x=0.0, slot=0, oid=None, live=5):
        """a fighter table entry (slot) with its module block, base accessor (posture, AttackModule)"""
        f = self.entries + slot * C.FIGHTER_ENTRY
        self.mu.mem_write(f, b'\0' * 0x80)
        n = max(self.w(self.ftab + 8), slot + 1)
        self.setw(self.ftab + 8, n)
        oid = (0x00010000 * (slot + 1)) | 0x12 if oid is None else oid
        self.setw(f, oid)
        self.setw(f + C.KIND_AT, kind)
        self.mu.mem_write(f + 0x1E, bytes([live]))
        acc = self.alloc(0x7400, b'\0')
        self.setw(f + C.ACC, acc)
        st = self.alloc(0x80, b'\0')
        self.setw(acc + C.STATUS_MOD, st)
        self.setw(st + 0x48, status)
        wm = self.alloc(0x20, b'\0')
        self.setw(wm, self.wm_vt)
        cats = self.alloc(0x40, b'\0')
        inst = self.alloc(0x20, b'\0')
        sw = self.alloc(0x20, b'\0')
        floats = self.alloc(0x40)
        flags = self.alloc(0x10)
        self.setw(wm + 8, cats)
        self.setw(cats, inst)
        self.setw(cats + 4, sw)
        self.setw(sw + 4, floats)
        self.setw(sw + 0x14, flags)
        self.setw(acc + C.WORK, wm)
        for i in range(16):
            self.setw(floats + 4 * i, fbits(100.0 + i))
        self.setw(flags, 0x0000C00F)
        self.setw(flags + 4, 0x12345678)
        posture = self.alloc(0x40, b'\0')
        self.setw(posture + 0x10, fbits(x))
        self.setw(acc + C.POSTURE, posture)
        self.setw(acc + C.SIDE_MOD, 0x7290AAAA)
        bacc = self.alloc(0x80, b'\0')                 # the base accessor (+0x18 posture, +0x50 AttackModule)
        self.setw(f + 0xC, bacc)
        bpost = self.alloc(0x40, b'\0')
        self.setw(bpost, self.post_vt)
        self.setw(bpost + 0x20, fbits(x))
        self.setw(bacc + C.BASE_POSTURE, bpost)
        m = 0
        if shield:
            m = self.alloc(0x50, b'\0')
            groups = self.alloc(5 * 0x34, b'\0')
            shapes = self.alloc(5 * 0x24, b'\0')
            self.setw(m + 8, groups)
            self.setw(m + 0xC + 4, shapes)
            self.setw(m + 0x14, 1)
            self.setw(m + 0x44, 0x4444)
            self.setw(m + 0x28, 1)
            for i in range(5):
                self.setw(shapes + 0x24 * i + 0x20, 0xFFFFFFFF)
            self.setw(acc + C.SHIELD, m)
        return dict(f=f, acc=acc, m=m, floats=floats, flags=flags, posture=posture, st=st, wm=wm, bacc=bacc,
                    oid=oid, bpost=bpost)

    def attack_records(self, fk, hits, parts=3, on=1):
        """fk's AttackModule with `parts` part groups; hits: {part: [object ids in its list, ...]} (node +0x27 the
        hitbox id = 5 + index)"""
        am = self.alloc(0x60, b'\0')
        vt = self.alloc(0x200, b'\0')
        self.setw(am, vt)
        self.setw(vt + 0x194, self.am_fn)
        self.setw(am + 0x4C, on)
        self.setw(am + 0x18, parts)
        arr = self.alloc(parts * 0x174, b'\0')
        self.setw(am + 0x14, arr)
        for p in range(parts):
            g = arr + p * 0x174
            sent = g + 0x124
            prev = sent
            ids = hits.get(p, [])
            nodes = [self.alloc(0x30, b'\0') for _ in ids]
            for k, (node, oid) in enumerate(zip(nodes, ids)):
                self.setw(node + 0x18, oid)
                self.mu.mem_write(node + 0x27, bytes([5 + k]))
                self.setw(node + 4, nodes[k + 1] if k + 1 < len(nodes) else sent)
            self.setw(g + 0x128, nodes[0] if nodes else sent)
            self.setw(sent, prev)
        self.setw(fk['bacc'] + C.BASE_ATTACK, am)
        return am

    def floats(self, fk):
        return [round(bitsf(self.w(fk['floats'] + 4 * i)), 4) for i in range(16)]

    def flagw(self, fk):
        return self.w(fk['flags']), self.w(fk['flags'] + 4)


def words_checks(base, patched):
    p = C.patches()
    img, pimg = K.Image(base), K.Image(patched)
    check('the patched RPX has every word', [hex(a) for a, w in sorted(p.items()) if pimg.w(a) != w][:4], [])
    check('the hooks\' words in the base are the game\'s', [hex(a) for a, w in C.ORIGINAL.items() if img.w(a) != w], [])
    check('no relocation on a hooked word', [hex(a) for a in C.ORIGINAL if a in img.relocs()], [])
    check('the cave space is free in the base', [hex(a) for a in range(C.CAVE, C.LIMIT, 4)
                                                 if C.word_or_0(img, a) != 0][:4], [])
    check('Mario\'s vtable slots 0 / 42 / 43 point at the hooked words',
          [img.w(C.MARIO_VT + 0xC + 8 * s) for s in (0, 42, 43)], [C.SETUP_HOOK, C.SLOT42_HOOK, C.SLOT43_HOOK])
    check('the words after the hooks unchanged (Mario\'s b 0x02F1A598, blr)',
          (pimg.w(C.SETUP_HOOK + 4), pimg.w(C.SLOT43_HOOK + 4)), (0x4BFFFEA4, 0x4E800020))


def setup_checks(e, kind):
    mk = e.fighter(0x12, slot=3)
    vl = e.alloc(0x200, b'\0')
    block = e.alloc(0x400, b'\0')
    mgr = e.alloc(0x2000, b'\0')
    e.setw(PARAM_MGR, mgr)
    e.setw(mgr + 0x1164, vl)
    e.setw(vl + 0x138, block)
    ints = e.alloc(0x400, b'\0')
    e.setw(e.w(e.w(mk['wm'] + 8)) + 0xC, ints)
    e.setw(ints + 0x12C, 2)
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
        check('group init arguments as Marth\'s (group struct, M+0x18, [M+0x44], M+0xC, count, group, first shape)',
              rel(inits[0], m), rel(marth[0], mm))
        check('  = group 1 at [M+8]+0x34, one shape, the first free one', rel(inits[0], m),
              (0x34, 0x18, 0x4444, 0xC, 1, 1, 1))
        check('group bytes +0x28..+0x2C as Marth\'s', inits[0][3][0x28:0x2D], marth[0][3][0x28:0x2D])
        ms = struct.unpack('>7fHB', marth[0][2][:0x1F])
        check('Marth\'s shape layout: x y z x y z radius bone type', ms, (1.5, 2.5, 3.5, 1.5, 2.5, 3.5, 4.5, 7, 2))
        ours = struct.unpack('>7fHB', inits[0][2][:0x1F])
        want = tuple(round(v, 4) for v in C.SHAPE['p1'] + C.SHAPE['p2'] + (C.SHAPE['radius'],)) + (C.SHAPE['bone'], 2)
        check('our shape: (0, 2.5, 0) - (0, 9.5, 0), radius 6.5, joint 0, a capsule',
              tuple(round(v, 4) for v in ours[:7]) + ours[7:], want)
    check('the module\'s shape count grows by one', e.w(m + 0x14), 2)
    shapes = e.w(m + 0xC + 4)
    check('the new shape (index 1) switched off, the guard\'s untouched',
          (e.w(shapes + 0x24 + 0x20), e.w(shapes + 0x20)), (0, 0xFFFFFFFF))
    check('groups on: unchanged (1)', e.w(m + 0x28), 1)
    check('then Mario\'s setup (fighter, r5 = 1)', [c for c in e.calls if c[0] == 'mario_setup'],
          [('mario_setup', sk['f'], 1)])
    check('registers and stack kept', kept, True)
    for what, fk in (('Mario (3)', e.fighter(MARIO)), ('Zelda (0x10)', e.fighter(0x10)),
                     ('kind 0x%X without a shield module' % kind, e.fighter(kind, shield=False))):
        r, kept = e.run(C.SETUP_HOOK, 0, fk['f'], 0)
        check('%s: no group built, Mario\'s setup with r5 = 1' % what, e.calls, [('mario_setup', fk['f'], 1)])
        if fk['m']:
            check('%s: module untouched' % what, (e.w(fk['m'] + 0x14), e.w(fk['m'] + 0x28)), (1, 1))
        check('%s: registers kept' % what, kept, True)


def message(e, damage=13.5, group=1, category=0, oid=None, hid=3, part=1):
    am = e.alloc(0x10, b'\0')
    vt = e.alloc(0x200, b'\0')
    e.setw(am, vt)
    e.setw(vt + 0x194, e.am_fn)
    rec = e.alloc(0x40, b'\0')
    e.setw(rec + 0x18, oid if oid is not None else ((category << 28) | 0x00120034))
    e.mu.mem_write(rec + 0x1C, bytes([category]))
    e.mu.mem_write(rec + 0x26, bytes([hid]))
    e.mu.mem_write(rec + 0x29, bytes([part]))
    msg = e.alloc(0x40, b'\0')
    e.setw(msg + 8, am)
    e.setw(msg + 0xC, fbits(damage))
    e.setw(msg + 0x10, rec)
    e.setw(msg + 0x14, group)
    e.setw(msg + 0x18, fbits(0.25))
    e.setw(msg + 0x1C, fbits(-0.75))
    return msg, am, rec


def hitdata(e, b54=0):
    h = e.alloc(0x68, b'\0')
    e.mu.mem_write(h + 0x54, bytes([b54]))
    e.hitdata = h
    return h


def slot42_checks(e, kind):
    base = [round(100.0 + i, 4) for i in range(16)]
    F0 = 0x0000C00F
    e.objects.clear()
    # a fighter attacker: its own place
    for my_x, ax, side in ((0.0, 20.0, 1.0), (30.0, 20.0, -1.0)):
        fk = e.fighter(kind, x=my_x)
        aid = 0x00030012
        e.obj(aid, x=ax, y=7.5)
        msg, am, rec = message(e, category=0, oid=aid)
        hd = hitdata(e)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        want = list(base)
        want[6], want[7], want[8], want[9] = 13.5, side, ax, 7.5
        check('slot 42, a fighter at %g (him at %g): damage, side %+g, its X / Y' % (ax, my_x, side), e.floats(fk), want)
        check('  flags 0x21000010 + 0x21000012 (found), not 0x21000011', e.flagw(fk), (F0 | 0x10000 | 0x40000, 0x12345678))
        check('  hit data asked with (AM, id, part)', [c for c in e.calls if c[0] == 'hitdata'], [('hitdata', am, 3, 1)])
        check('  its handle from its id', [c[3:] for c in e.calls if c[0] == 'handle'], [(aid, 0)])
        check('  registers kept', kept, True)
    # a weapon / an item: the current owner's place, the side from the owner
    for cat, label in ((1, 'weapon'), (2, 'item')):
        fk = e.fighter(kind, status=C.ST_UI, x=0.0)
        e.obj(0x00040012, x=-25.0, y=3.0)
        e.obj((cat << 28) | 0x0000ABCD, x=10.0, y=5.0, owner=0x00040012)
        msg, am, rec = message(e, damage=9.0, category=cat, oid=(cat << 28) | 0x0000ABCD)
        hitdata(e)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('slot 42, the transformation (0x157), a %s: not countered (XV2: CounterMelee only)' % label,
              (e.floats(fk), e.flagw(fk), kept), (base, (F0, 0x12345678), True))
        fk = e.fighter(kind, status=C.ST_SS, x=0.0)
        owner = 0x00040012
        e.obj(owner, x=-25.0, y=3.0)
        wid = (cat << 28) | 0x0000ABCD
        e.obj(wid, x=10.0, y=5.0, owner=owner)
        msg, am, rec = message(e, damage=9.0, category=cat, oid=wid)
        hitdata(e)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        want = list(base)
        want[6], want[7], want[8], want[9] = 9.0, -1.0, -25.0, 3.0
        check('slot 42, Secret Sensation, a %s at +10 fired by a fighter at -25: the owner\'s X / Y, side -1' % label, e.floats(fk), want)
        check('  flags 0x21000010 + 11 (not a fighter) + 12 (found)', e.flagw(fk), (F0 | 0x70000, 0x12345678))
        check('  handles: the %s, then its owner' % label, [c[3] for c in e.calls if c[0] == 'handle'], [wid, owner])
        check('  registers kept', kept, True)
    # a weapon whose owner isn't a fighter / is gone / has no owner module: the side from the weapon
    for what, owner, alive_owner, has_om in (('owner a gimmick id', 0x30000005, True, True),
                                             ('owner 0x50000000 (none)', 0x50000000, True, True),
                                             ('owner gone', 0x00050012, False, True),
                                             ('no owner module', None, True, False)):
        fk = e.fighter(kind, status=C.ST_SS, x=0.0)
        if owner is not None and owner >> 28 == 0:
            e.obj(owner, x=-40.0, alive=alive_owner)
        wid = 0x1000BEEF
        e.obj(wid, x=12.0, owner=owner if has_om else None)
        msg, am, rec = message(e, damage=5.0, category=1, oid=wid)
        hitdata(e)
        e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        want = list(base)
        want[6], want[7] = 5.0, 1.0
        check('slot 42, a weapon at +12, %s: no target, the side from the weapon (+1)' % what, e.floats(fk), want)
        check('  flags 0x21000010 + 11, not 12', e.flagw(fk), (F0 | 0x30000, 0x12345678))
    # an item whose object is gone: Marth's side function
    fk = e.fighter(kind, status=C.ST_SS)
    e.side = -0.5
    msg, am, rec = message(e, damage=11.0, category=2, oid=0x2000FFFF)
    hd = hitdata(e)
    e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    want = list(base)
    want[6], want[7] = 11.0, -0.5
    check('slot 42, a gone item: Marth\'s side (-0.5), not found', (e.floats(fk), e.flagw(fk)),
          (want, (F0 | 0x30000, 0x12345678)))
    check('  0x02C22684 with Marth\'s arguments', [c for c in e.calls if c[0] == 'side'],
          [('side', 0x7290AAAA, am, hd, 3, 1, 0.25, -0.75)])
    # a stage gimmick (category 3): not countered (either status)
    fk = e.fighter(kind, status=C.ST_SS)
    msg, am, rec = message(e, damage=11.0, category=3, oid=0x30001234)
    hitdata(e)
    r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    check('slot 42, a stage gimmick (category 3): nothing written, nothing called',
          (e.floats(fk), e.flagw(fk), e.calls, kept), (base, (F0, 0x12345678), [], True))
    # Secret Sensation (0x155): recorded as in 0x157
    fk = e.fighter(kind, status=C.ST_SS, x=0.0)
    aid = 0x00030012
    e.obj(aid, x=-20.0, y=4.0)
    msg, am, rec = message(e, category=0, oid=aid)
    hitdata(e)
    r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    want = list(base)
    want[6], want[7], want[8], want[9] = 13.5, -1.0, -20.0, 4.0
    check('slot 42, Secret Sensation (0x155), a fighter to his left: recorded', (e.floats(fk), e.flagw(fk), kept),
          (want, (F0 | 0x50000, 0x12345678), True))
    # nothing
    fk = e.fighter(kind)
    e.setw(fk['flags'], F0 | 0x10000)
    msg, am, rec = message(e, damage=40.0)
    hitdata(e)
    e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    check('slot 42, second hit: nothing written, nothing called',
          (e.floats(fk), e.flagw(fk), e.calls), (base, (F0 | 0x10000, 0x12345678), []))
    for what, fkw, kw, hd in (('group 0 (the guard)', dict(kind=kind), {'group': 0}, {}),
                              ('status 0x158', dict(kind=kind, status=0x158), {}, {}),
                              ('Wait (0)', dict(kind=kind, status=0), {}, {}),
                              ('Mario (3) in 0x157', dict(kind=MARIO), {}, {}),
                              ('uncounterable (+0x54)', dict(kind=kind), {}, {'b54': 1})):
        fk = e.fighter(**fkw)               # (one table entry: made just before its run)
        msg, am, rec = message(e, **kw)
        hitdata(e, **hd)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('slot 42, %s: nothing written' % what, (e.floats(fk), e.flagw(fk)), (base, (F0, 0x12345678)))
        check('slot 42, %s: registers kept' % what, kept, True)


def slot43_case(e, kind, status=0, form=2000.0, my_x=0.0, att_x=20.0, records='attacker', b54=0, live=5,
                rec_on=1, part=1, before=()):
    """him in slot 0 of the table; an attacker (slot 1) whose records hold him (or not); returns (r, kept, msg, att)"""
    e.setw(e.ftab + 8, 0)
    sk = e.fighter(kind, status=status, x=my_x, slot=0)
    att = e.fighter(0x12, status=0x25, x=att_x, slot=1, live=live)
    other = e.fighter(0x5, status=0, x=-50.0, slot=2)
    e.attack_records(other, {0: [0x00090012]})
    hits = {}
    if records == 'attacker':
        hits = {part: list(before) + [sk['oid']]}
    e.attack_records(att, hits, parts=3, on=rec_on)
    if records == 'self':
        e.attack_records(sk, {0: [sk['oid']]})
    e.vars = {C.V_FORM: form, C.V_DODGE_R: 0.0, C.V_DODGE_L: 0.0}
    hitdata(e, b54)
    msg = e.alloc(0x20, b'\0')
    e.mu.mem_write(msg + 8, bytes([0x40]))
    r, kept = e.run(C.SLOT43_HOOK, 0, sk['f'], msg)
    return r, kept, msg, sk, att


def slot43_checks(e, kind):
    for st in (C.ST_UI,):
        for form in (0.0, 2000.0):
            e.setw(e.ftab + 8, 0)
            sk = e.fighter(kind, status=st)
            msg = e.alloc(0x20, b'\0')
            e.mu.mem_write(msg + 8, bytes([0x40]))
            r, kept = e.run(C.SLOT43_HOOK, 0, sk['f'], msg)
            check('slot 43, status 0x157 (TIMER_0 %g): 0, handled, nothing else called' % form,
                  (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept), (0, 0x41, [], True))
    for st, name in ((0, 'Wait'), (1, 'Walk'), (2, 'WalkBrake'), (0x11, 'Squat'), (0x12, 'SquatWait'),
                     (0x13, 'SquatF'), (0x14, 'SquatB'), (0x15, 'SquatRv')):
        for my_x, att_x, timer, other in ((0.0, 20.0, C.V_DODGE_R, C.V_DODGE_L), (40.0, 20.0, C.V_DODGE_L, C.V_DODGE_R)):
            r, kept, msg, sk, att = slot43_case(e, kind, status=st, my_x=my_x, att_x=att_x)
            side = 'right' if timer == C.V_DODGE_R else 'left'
            check('slot 43, transformed, %s, a fighter to his %s: 0, handled' % (name, side),
                  (r, bytes(e.mu.mem_read(msg + 8, 1))[0]), (0, 0x41))
            check('  TIMER_%d = 4, TIMER_%d = 0 through set_float on his WorkModule' % (timer - C.V_FORM, other - C.V_FORM),
                  [c[1:] for c in e.calls if c[0] == 'set'], [(sk['wm'], timer, 4.0), (sk['wm'], other, 0.0)])
            if st == 0 and my_x == 0.0:
                check('  TIMER_0 read through get_float', [c[1:] for c in e.calls if c[0] == 'get'], [(sk['wm'], C.V_FORM)])
                am = e.w(att['bacc'] + C.BASE_ATTACK)
                check('  hit data asked with (its AM, node +0x27, the part)', [c[1:] for c in e.calls if c[0] == 'hitdata'],
                      [(am, 5, 1)])
                check('  its place from its posture (vt +0x44)', [c[1:] for c in e.calls if c[0] == 'posture'],
                      [(att['bpost'],)])
            check('  registers kept', kept, True)
    for what, kw in (('the record after two other nodes in part 2', dict(part=2, before=(0x111, 0x222))),
                     ('the record in part 0', dict(part=0))):
        r, kept, msg, sk, att = slot43_case(e, kind, **kw)
        check('slot 43, %s: 0, TIMER_1 4' % what, (r, e.vars.get(C.V_DODGE_R)), (0, 4.0))
    for what, kw in (('no fighter\'s records hold him (a weapon / item / gimmick)', dict(records=None)),
                     ('only his own records', dict(records='self')),
                     ('the attacker not live', dict(live=2)),
                     ('records off (+0x4C 0)', dict(rec_on=0)),
                     ('transforming (TIMER_0 1000)', dict(form=1000.0)),
                     ('not transformed (TIMER_0 0)', dict(form=0.0)),
                     ('uncounterable (+0x54)', dict(b54=1)),
                     ('Dash (3)', dict(status=3)), ('Fall (0xE)', dict(status=0xE)),
                     ('Squat - 1 (0x10)', dict(status=0x10)), ('Landing (0x16)', dict(status=0x16)),
                     ('Guard (0x1C)', dict(status=0x1C)), ('Damage (0x45)', dict(status=0x45)),
                     ('the dodge (0x158)', dict(status=0x158))):
        r, kept, msg, sk, att = slot43_case(e, kind, **kw)
        check('slot 43, %s: 1, message untouched, nothing set' % what,
              (r, bytes(e.mu.mem_read(msg + 8, 1))[0], [c for c in e.calls if c[0] == 'set'], kept), (1, 0x40, [], True))
    for flag, want in ((True, 0), (False, 1)):
        e.setw(e.ftab + 8, 0)
        sk = e.fighter(kind, status=C.ST_SS)
        if flag:
            e.setw(sk['flags'], 0x0000C00F | 0x10000)
        msg = e.alloc(0x20, b'\0')
        e.mu.mem_write(msg + 8, bytes([0x40]))
        r, kept = e.run(C.SLOT43_HOOK, 0, sk['f'], msg)
        check('slot 43, Secret Sensation (0x155), 0x21000010 %s: %d' % ('on' if flag else 'off', want),
              (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept), (want, 0x41 if want == 0 else 0x40, [], True))
    r, kept, msg, sk, att = slot43_case(e, kind, status=C.ST_SS, form=2000.0)
    check('slot 43, 0x155 without the flag, transformed, a fighter\'s records hold him: 1 (no dodge in a move)',
          (r, [c for c in e.calls if c[0] == 'set']), (1, []))
    r, kept, msg, sk, att = slot43_case(e, MARIO)
    check('slot 43, Mario (3) in Wait, a fighter\'s records hold him: 1, nothing read or set',
          (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept), (1, 0x40, [], True))
    e.setw(e.ftab + 8, 0)
    sk = e.fighter(MARIO, status=C.ST_UI)
    msg = e.alloc(0x20, b'\0')
    e.mu.mem_write(msg + 8, bytes([0x40]))
    r, kept = e.run(C.SLOT43_HOOK, 0, sk['f'], msg)
    check('slot 43, Mario (3) in 0x157: 1 (Mario\'s stub)', (r, bytes(e.mu.mem_read(msg + 8, 1))[0]), (1, 0x40))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    base = a[0]
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
    check('Supamario\'s kind from extra_kinds.json', kind, 0x41)
    words_checks(base, patched)
    e = Run(patched)
    setup_checks(e, kind)
    slot42_checks(e, kind)
    slot43_checks(e, kind)
    print('%d failure(s)' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
