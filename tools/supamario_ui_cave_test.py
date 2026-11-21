#!/usr/bin/env python3
"""Runs tools/supamario_ui_cave.py's code in unicorn, in a patched RPX (Supamario's Ultra Instinct: the counter shape,
the counter's record and the autododge).

  python3 tools/supamario_ui_cave_test.py BASE.rpx [PATCHED.rpx [DIAG.rpx]]

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
- v5: the transformation / its counter is status 0x155 with TIMER_4 (C.V_MODE) 7, the dodge 0x155 with 5 (Mario's
  F.L.U.D.D. statuses 0x157 / 0x158 are nothing special any more); the TIMER_4 read goes through get_float;
- slot 42: kind 0x41, group 1, status 0x155 (the transformation: TIMER_4 7), first hit: float 6 = the damage, 7 = the side, 8 / 9 = the X / Y of the
  fighter to answer, flags 0x21000010 (+ 0x21000011 not a fighter, + 0x21000012 found); a fighter attacker: its own place
  (left / right); a weapon: its current owner's place (owner module +0x34), the side from the owner; an item the same; a
  weapon whose owner is no fighter (a gimmick's id) or gone: no target, the side from the weapon's place; a stage gimmick
  (category 3) whose object is gone: Marth's side function's value; nothing for: a second hit, group 0, another status,
  an uncounterable hit (+0x54), Mario's kind (3); registers kept;
- ui4: the native events (registration code: 0x10 -> slot 42, 0x12 -> slot 43 = the shield damage, 0xB / 0xC the body
  damage with no slot before the damage add); the autododge in slot 42 (Wait / Walk / WalkBrake / Squat .. SquatRv,
  transformed: TIMER_1 / 2 by the hitting object's side; Marth's side when it is gone; nothing otherwise) and slot 43 in
  those statuses (0, handled: no guard damage); category-4 items in Secret Sensation and the owner chain; the name
  walk's alignment test a nop; diag S4UF, the effect runtime's messages, S4U3 st / t0 / ret, S4U2's dodge bits.
  (Below, v1-v4's slot 43 autododge through the fighters' hit records no longer exists.)
- slot 43: 0x155 with TIMER_4 7 -> 0 and the handled bit whatever else; transformed (TIMER_0 > 1500) in Wait / Walk / WalkBrake /
  Squat .. SquatRv with a fighter's hit records holding him -> 0, the handled bit, TIMER_1 (attacker right) or TIMER_2
  (left) = 4.0 and the other 0 through set_float, the hit data asked with (AM, node +0x27, part); the record found in a
  later part / after other nodes / of the second live fighter; -> 1 and nothing written for: no fighter's records (a
  weapon / item / gimmick hit), records of a dead fighter, his own records, records off (+0x4C 0), not transformed
  (TIMER_0 1000 / 0), another status (Dash 3, Fall 0xE, Damage 0x45, Guard 0x1C, v1-v4's 0x157 / 0x158), an uncounterable
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
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_MSR, UC_PPC_REG_LR,  # noqa: E402
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
        self.links = {}                  # LinkModule -> link 0's id (None: no link 0)
        self.lm_has = self.alloc(4)
        self.stub(self.lm_has, self.link_has)
        self.lm_get = self.alloc(4)
        self.stub(self.lm_get, self.link_id)
        self.lm_vt = self.alloc(0x100, b'\0')
        self.setw(self.lm_vt + 0x5C, self.lm_has)
        self.setw(self.lm_vt + 0x6C, self.lm_get)

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
    def link_has(self, e):
        self.rec('link_has', 3, 4)
        return 1 if self.links.get(self.r(3)) is not None else 0

    def link_id(self, e):
        self.rec('link_id', 3, 4, 5)
        return self.links.get(self.r(3), 0x50000000)

    def obj(self, oid, x=0.0, y=0.0, alive=True, owner=None, link=None):
        """a weapon / item / gimmick object: its entry (+0xC its accessor: +0x6C the team / owner module, +0x68 its
        LinkModule when `link` (link 0's object id; False: a LinkModule without link 0))"""
        entry = self.alloc(0x40, b'\0')
        acc = self.alloc(0x80, b'\0')
        self.setw(entry, oid)
        self.setw(entry + 0xC, acc)
        if link is not None:
            lm = self.alloc(0x20, b'\0')
            self.setw(lm, self.lm_vt)
            self.setw(acc + C.BASE_LINK, lm)
            self.links[lm] = None if link is False else link
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
    check('ui4: Mesh_Visibility\'s name walk (mesh_vis_cave in the base): the name pointer\'s alignment test '
          '(andi. r0, r3, 3 after the mesh\'s vt +0x2C) in the base, a nop in the patched RPX, its neighbours unchanged',
          ([hex(a) for a, w in C.WALK_WORDS.items() if img.w(a) != w], hex(pimg.w(C.WALK_FIX)),
           [hex(a) for a, w in C.WALK_WORDS.items() if a != C.WALK_FIX and pimg.w(a) != w]), ([], hex(C.NOP), []))
    check('the words after the hooks unchanged (Mario\'s b 0x02F1A598, blr)',
          (pimg.w(C.SETUP_HOOK + 4), pimg.w(C.SLOT43_HOOK + 4)), (0x4BFFFEA4, 0x4E800020))


EVENT_REG = (0x02E14288, 0x02E14600)   # the fighter's event handler registrations (0x02E3C1BC(listener, id, r5, &entry))
EVENT_ADD = 0x02E3C1BC
SPEC = 0x7538                           # the fighter's specializer (vtable slot n at +0xC + 8n)
DAMAGE_ADD = 0x02E29C28                 # the damage add (fighter, 1, f1 the damage) of events 0xB / 0xC


def _events(img):
    """{event id: handler} read from the registration code: `lis r, 0x1012; lwzu rX, lo(r)` (the {flags, fn} entry), `li
    r4, id`, `bl 0x02E3C1BC`"""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    out, entry, ev, hi = {}, None, None, {}
    for a in range(*EVENT_REG, 4):
        w = img.w(a)
        op = w >> 26
        rd, ra, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if op == 15 and ra == 0:
            hi[rd] = imm << 16
        elif op == 33 and ra in hi:          # lwzu rD, d(rA)
            entry = hi[ra] + simm
        elif op == 14 and ra == 0 and rd == 4:
            ev = simm
        elif op == 18 and w & 1 and entry is not None and ev is not None:
            off = w & 0x3FFFFFC
            if off & 0x2000000:
                off -= 0x4000000
            if a + off == EVENT_ADD:
                out[ev] = img.w(entry + 4)
                entry = None
    return out


def _slot_calls(img, fn, limit):
    """the specializer slots a handler calls ([fighter + 0x7538] vt +0xC + 8n) before `limit` words, in order, with the
    word index; and the index of its first bl to DAMAGE_ADD"""
    slots, dmg = [], None
    for k in range(limit):
        a = fn + 4 * k
        w = img.w(a)
        if w >> 26 == 32 and w & 0xFFFF == SPEC:
            for j in range(1, 6):
                x = img.w(a + 4 * j)
                if x >> 26 == 32 and (x & 0xFFFF) >= 0xC and ((x & 0xFFFF) - 0xC) % 8 == 0 and (x >> 16) & 31 != 1:
                    slots.append(((x & 0xFFFF) - 0xC) // 8)
                    break
        if w >> 26 == 18 and w & 1 and dmg is None:
            off = w & 0x3FFFFFC
            if off & 0x2000000:
                off -= 0x4000000
            if a + off == DAMAGE_ADD:
                dmg = (k, len(slots))
    return slots, dmg


def event_checks(base):
    """ui4: which game event calls which of Mario's specializer slots (static reading of the base, the events' own
    registration code). v1-v4 took slot 43 for the body's damage veto: it is called by event 0x12, the shield damage
    right after the shield hit (event 0x10, slot 42); the body hit's damage (events 0xB / 0xC) is added before any
    specializer slot is asked. The v4 log agrees: slot 43 ran only after slot 42, never for DK's punches"""
    img = K.Image(base)
    ev = _events(img)
    check('native: the fighter\'s event handlers as registered (0x10 the shield hit, 0x12 the shield damage, 0xB / 0xC '
          'the body damage)', {k: ev.get(k) for k in (0xB, 0xC, 0x10, 0x12)},
          {0xB: 0x02E2AFBC, 0xC: 0x02E2B59C, 0x10: 0x02E35794, 0x12: 0x02E35EE4})
    check('native: event 0x10 asks slot 42 (the cave\'s counter / autododge), event 0x12 slot 43 first (the cave\'s '
          'shield-damage skip)', (_slot_calls(img, ev[0x10], 40)[0][:1], _slot_calls(img, ev[0x12], 16)[0][:1]),
          ([42], [43]))
    for e_ in (0xB, 0xC):
        slots, dmg = _slot_calls(img, ev[e_], 0x170)
        check('native: event 0x%X (the body damage, 0x%08X) adds the damage (0x%08X) before asking any specializer '
              'slot, and never asks 42 / 43: no slot vetoes a body hit (the v1-v4 autododge\'s mistake)'
              % (e_, ev[e_], DAMAGE_ADD), (dmg is not None and dmg[1] == 0, 42 in slots or 43 in slots), (True, False))


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
        e.vars = {C.V_MODE: C.MODE_FORM}
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
        check('  TIMER_4 (the mode) read through get_float', [c[1:] for c in e.calls if c[0] == 'get'],
              [(fk['wm'], C.V_MODE)])
    # a weapon / an item: the current owner's place, the side from the owner
    for cat, label in ((1, 'weapon'), (2, 'item')):
        e.vars = {C.V_MODE: C.MODE_FORM}
        fk = e.fighter(kind, status=C.ST_UI, x=0.0)
        e.obj(0x00040012, x=-25.0, y=3.0)
        e.obj((cat << 28) | 0x0000ABCD, x=10.0, y=5.0, owner=0x00040012)
        msg, am, rec = message(e, damage=9.0, category=cat, oid=(cat << 28) | 0x0000ABCD)
        hitdata(e)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('slot 42, the transformation (0x155, TIMER_4 7), a %s: not countered (XV2: CounterMelee only)' % label,
              (e.floats(fk), e.flagw(fk), kept), (base, (F0, 0x12345678), True))
        for mode in (C.MODE_DODGE, 3.0):
            e.vars = {C.V_MODE: mode}
            fk = e.fighter(kind, status=C.ST_SS, x=0.0)
            e.obj(0x00040012, x=-25.0, y=3.0)
            e.obj((cat << 28) | 0x0000ABCD, x=10.0, y=5.0, owner=0x00040012)
            msg, am, rec = message(e, damage=9.0, category=cat, oid=(cat << 28) | 0x0000ABCD)
            hitdata(e)
            e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
            check('  0x155 with TIMER_4 %g (not the transformation): the %s recorded' % (mode, label),
                  e.flagw(fk)[0] & 0x10000, 0x10000)
        e.vars = {}
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
    # ui4: an item is category 4 in game (the Killer Eye 0x4001000x in the v4 log): Secret Sensation answers its owner
    e.vars = {}
    fk = e.fighter(kind, status=C.ST_SS, x=0.0)
    owner = 0x00020012
    e.obj(owner, x=-25.0, y=3.0)
    iid = 0x40010000
    e.obj(iid, x=10.0, y=5.0, owner=owner)
    msg, am, rec = message(e, damage=9.0, category=4, oid=iid)
    hitdata(e)
    r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    want = list(base)
    want[6], want[7], want[8], want[9] = 9.0, -1.0, -25.0, 3.0
    check('ui4: slot 42, Secret Sensation, an item of category 4 (0x40010000) placed by a fighter at -25: its owner\'s '
          'X / Y, flags 10 + 11 + 12', (e.floats(fk), e.flagw(fk), kept), (want, (F0 | 0x70000, 0x12345678), True))
    for cat in (5, 7):
        fk = e.fighter(kind, status=C.ST_SS)
        msg, am, rec = message(e, damage=11.0, category=cat, oid=(cat << 28) | 0x1234)
        hitdata(e)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('ui4: slot 42, Secret Sensation, category %d: nothing written, nothing called' % cat,
              (e.floats(fk), e.flagw(fk), e.calls, kept), (base, (F0, 0x12345678), [], True))
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
                              ('status 0x158 (v1-v4\'s dodge)', dict(kind=kind, status=C.OLD_ST_DODGE), {}, {}),
                              ('status 0x157 (v1-v4\'s transformation)', dict(kind=kind, status=C.OLD_ST_UI), {}, {}),
                              ('Wait (0), not transformed (ui4: the autododge\'s path)', dict(kind=kind, status=0),
                               {}, {}),
                              ('Mario (3) in 0x155', dict(kind=MARIO), {}, {}),
                              ('uncounterable (+0x54)', dict(kind=kind), {}, {'b54': 1})):
        fk = e.fighter(**fkw)               # (one table entry: made just before its run)
        msg, am, rec = message(e, **kw)
        hitdata(e, **hd)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        check('slot 42, %s: nothing written' % what, (e.floats(fk), e.flagw(fk)), (base, (F0, 0x12345678)))
        check('slot 42, %s: registers kept' % what, kept, True)


DODGE_STATUSES = ((0, 'Wait'), (1, 'Walk'), (2, 'WalkBrake'), (0x11, 'Squat'), (0x12, 'SquatWait'), (0x13, 'SquatF'),
                  (0x14, 'SquatB'), (0x15, 'SquatRv'))
NOT_DODGE = ((3, 'Dash'), (0xE, 'Fall'), (0x10, 'Squat - 1 (0x10)'), (0x16, 'Landing (0x16)'), (0x1C, 'Guard'),
             (0x45, 'Damage'), (C.OLD_ST_DODGE, 'v1-v4\'s dodge (0x158)'), (C.OLD_ST_UI, 'v1-v4\'s transformation (0x157)'))


def dodge42_case(e, kind, status=0, form=2000.0, my_x=0.0, obj_x=20.0, category=0, alive=True, group=1, mode=0.0):
    """ui4: the autododge (slot 42 in a dodge status: the shape on while transformed); him in slot 0, the object that
    hit the shape at obj_x; returns (r, kept, sk, msg, am, hd)"""
    e.setw(e.ftab + 8, 0)
    e.objects.clear()
    sk = e.fighter(kind, status=status, x=my_x, slot=0)
    oid = (category << 28) | 0x00030012
    if alive is not None:
        e.obj(oid, x=obj_x, y=4.0, alive=alive)
    e.vars = {C.V_FORM: form, C.V_DODGE_R: 0.0, C.V_DODGE_L: 0.0, C.V_MODE: mode}
    msg, am, rec = message(e, damage=8.0, group=group, category=category, oid=oid)
    hd = hitdata(e)
    r, kept = e.run(C.SLOT42_HOOK, 0, sk['f'], msg)
    return r, kept, sk, msg, am, hd


def dodge42_checks(e, kind):
    """ui4: the autododge through the counter shape (slot 42 in Wait / Walk / WalkBrake / Squat .. SquatRv)"""
    base = [round(100.0 + i, 4) for i in range(16)]
    F0 = 0x0000C00F
    for st, name in DODGE_STATUSES:
        for my_x, ox, timer, other in ((0.0, 20.0, C.V_DODGE_R, C.V_DODGE_L), (40.0, 20.0, C.V_DODGE_L, C.V_DODGE_R)):
            r, kept, sk, msg, am, hd = dodge42_case(e, kind, status=st, my_x=my_x, obj_x=ox)
            side = 'right' if timer == C.V_DODGE_R else 'left'
            check('ui4: slot 42, transformed, %s, a fighter\'s hit on the shape, it to his %s: TIMER_%d = 4, TIMER_%d = 0 '
                  'through set_float on his WorkModule' % (name, side, timer - C.V_FORM, other - C.V_FORM),
                  [c[1:] for c in e.calls if c[0] == 'set'], [(sk['wm'], timer, 4.0), (sk['wm'], other, 0.0)])
            if st == 0 and my_x == 0.0:
                check('  TIMER_0 read through get_float (only it)', [c[1:] for c in e.calls if c[0] == 'get'],
                      [(sk['wm'], C.V_FORM)])
                check('  its place from its handle', [c[3] for c in e.calls if c[0] == 'handle'], [0x00030012])
                check('  the status work untouched (floats 6-9, flags), the message untouched, no hit data asked',
                      (e.floats(sk), e.flagw(sk), bytes(e.mu.mem_read(msg + 8, 4)), [c for c in e.calls
                                                                                     if c[0] == 'hitdata']),
                      (base, (F0, 0x12345678), struct.pack('>I', am), []))
            check('  registers kept', kept, True)
    for cat, what in ((1, 'a weapon'), (2, 'category 2'), (4, 'an item (category 4)'), (3, 'a stage gimmick (3)')):
        r, kept, sk, msg, am, hd = dodge42_case(e, kind, category=cat, obj_x=-15.0)
        check('ui4: slot 42, transformed, Wait, %s at -15 on the shape: dodged (the shape blocks whatever reaches it): '
              'TIMER_2' % what, (e.vars.get(C.V_DODGE_L), e.vars.get(C.V_DODGE_R), kept), (4.0, 0.0, True))
    for sidev, timer in ((-0.5, C.V_DODGE_L), (0.5, C.V_DODGE_R)):
        e.side = sidev
        r, kept, sk, msg, am, hd = dodge42_case(e, kind, alive=None)
        check('ui4: slot 42, the object gone: Marth\'s side (%+g) -> TIMER_%d' % (sidev, timer - C.V_FORM),
              (e.vars.get(timer), [c for c in e.calls if c[0] == 'side'], kept),
              (4.0, [('side', 0x7290AAAA, am, hd, 3, 1, 0.25, -0.75)], True))
    e.side = -0.5
    for what, kw in (('transforming (TIMER_0 1000)', dict(form=1000.0)), ('not transformed (TIMER_0 0)', dict(form=0.0)),
                     ('group 0 (the guard)', dict(group=0))):
        r, kept, sk, msg, am, hd = dodge42_case(e, kind, **kw)
        check('ui4: slot 42, Wait, %s: nothing set, the status work untouched' % what,
              ([c for c in e.calls if c[0] == 'set'], e.floats(sk), e.flagw(sk), kept), ([], base, (F0, 0x12345678),
                                                                                         True))
    for st, name in NOT_DODGE:
        r, kept, sk, msg, am, hd = dodge42_case(e, kind, status=st)
        check('ui4: slot 42, transformed, %s: no dodge, nothing read or set' % name,
              ([c for c in e.calls if c[0] in ('set', 'get')], e.floats(sk), kept), ([], base, True))
    r, kept, sk, msg, am, hd = dodge42_case(e, MARIO)
    check('ui4: slot 42, Mario (3) in Wait: nothing read, set or called', (e.calls, kept), ([], True))


def slot43_case(e, kind, status=0, form=2000.0, mode=0.0, flag=False):
    """him in slot 0; slot 43 (event 0x12, the shield damage after a shield hit); returns (r, kept, msg, sk)"""
    e.setw(e.ftab + 8, 0)
    sk = e.fighter(kind, status=status, slot=0)
    if flag:
        e.setw(sk['flags'], 0x0000C00F | 0x10000)
    e.vars = {C.V_FORM: form, C.V_DODGE_R: 0.0, C.V_DODGE_L: 0.0, C.V_MODE: mode}
    msg = e.alloc(0x20, b'\0')
    e.mu.mem_write(msg + 8, bytes([0x40]))
    r, kept = e.run(C.SLOT43_HOOK, 0, sk['f'], msg)
    return r, kept, msg, sk


def slot43_checks(e, kind):
    """slot 43 = event 0x12 (0x02E35EE4), the shield DAMAGE following a shield hit (ui4: v1-v4 took it for the body's
    damage event; the v4 log has it only right after slot 42)"""
    for mode in (C.MODE_FORM, C.MODE_FORM - 1.0):
        for form in (0.0, 2000.0):
            r, kept, msg, sk = slot43_case(e, kind, status=C.ST_UI, form=form, mode=mode)
            check('slot 43, the transformation (0x155, TIMER_4 %g, TIMER_0 %g): 0, handled, only TIMER_4 read'
                  % (mode, form), (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept),
                  (0, 0x41, [('get', sk['wm'], C.V_MODE)], True))
    for mode, what in ((C.MODE_DODGE, 'the dodge'), (C.MODE_DODGE - 1.0, 'the dodge a frame on'), (0.0, 'Fake Death')):
        r, kept, msg, sk = slot43_case(e, kind, status=C.ST_SS, mode=mode)
        check('slot 43, 0x155 with TIMER_4 %g (%s): 1, message untouched' % (mode, what),
              (r, bytes(e.mu.mem_read(msg + 8, 1))[0], kept), (1, 0x40, True))
    for st, name in DODGE_STATUSES:
        r, kept, msg, sk = slot43_case(e, kind, status=st)
        check('ui4: slot 43, transformed, %s (the autododge\'s shape hit): 0, handled (no guard damage / stun), only '
              'TIMER_0 read, nothing set' % name, (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept),
              (0, 0x41, [('get', sk['wm'], C.V_FORM)], True))
    for form in (1000.0, 0.0):
        r, kept, msg, sk = slot43_case(e, kind, status=0, form=form)
        check('ui4: slot 43, Wait, TIMER_0 %g (not transformed): 1, message untouched' % form,
              (r, bytes(e.mu.mem_read(msg + 8, 1))[0], kept), (1, 0x40, True))
    for st, name in NOT_DODGE:
        r, kept, msg, sk = slot43_case(e, kind, status=st)
        check('ui4: slot 43, transformed, %s: 1, message untouched, nothing read' % name,
              (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept), (1, 0x40, [], True))
    for flag, want in ((True, 0), (False, 1)):
        r, kept, msg, sk = slot43_case(e, kind, status=C.ST_SS, mode=3.0, flag=flag)
        check('slot 43, Secret Sensation (0x155, TIMER_4 3), 0x21000010 %s: %d' % ('on' if flag else 'off', want),
              (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept),
              (want, 0x41 if want == 0 else 0x40, [] if flag else [('get', sk['wm'], C.V_MODE)], True))
    r, kept, msg, sk = slot43_case(e, MARIO, status=0)
    check('slot 43, Mario (3) in Wait: 1, nothing read', (r, bytes(e.mu.mem_read(msg + 8, 1))[0], e.calls, kept),
          (1, 0x40, [], True))
    r, kept, msg, sk = slot43_case(e, MARIO, status=C.ST_UI, mode=C.MODE_FORM)
    check('slot 43, Mario (3) in 0x155 with TIMER_4 7: 1 (Mario\'s stub)', (r, bytes(e.mu.mem_read(msg + 8, 1))[0]),
          (1, 0x40))


def chain_checks(e, kind):
    """v4: the owner chain (a projectile's / item's owner followed to a fighter)"""
    e.vars = {}                          # v5: TIMER_4 0 (Secret Sensation's rules, not the transformation's)
    base = [round(100.0 + i, 4) for i in range(16)]
    F0 = 0x0000C00F
    e.objects.clear()
    dk = 0x00020012
    cases = [
        # (what, objects: [(id, x, y, owner (+0x34), link)], the hit object, want (x, y) or None)
        ('a Killer Eye\'s shot: shot -> the Killer Eye (an item, +0x34) -> its thrower Donkey Kong (+0x34)',
         [(dk, -30.0, 2.0, None, None), (0x20000777, 15.0, 4.0, dk, None), (0x10000888, 8.0, 4.0, 0x20000777, None)],
         0x10000888, (-30.0, 2.0)),
        ('a Killer Eye\'s shot: the shot\'s owner by LinkModule link 0 (no +0x34), the item\'s by +0x34',
         [(dk, -30.0, 2.0, None, None), (0x20000777, 15.0, 4.0, dk, None), (0x10000888, 8.0, 4.0, None, 0x20000777)],
         0x10000888, (-30.0, 2.0)),
        ('Link\'s arrow: +0x34 none (0x50000000), LinkModule link 0 = Link',
         [(dk, 40.0, 1.0, None, None), (0x10000999, 9.0, 3.0, 0x50000000, dk)], 0x10000999, (40.0, 1.0)),
        ('Samus\'s missile: +0x34 = Samus (the v3 path)',
         [(dk, 40.0, 1.0, None, None), (0x10000AAA, 9.0, 3.0, dk, False)], 0x10000AAA, (40.0, 1.0)),
        ('an article\'s projectile: shot -> article (a weapon, link 0) -> its fighter (+0x34)',
         [(dk, -12.0, 6.0, None, None), (0x10000BB1, 3.0, 3.0, dk, None), (0x10000BB2, 6.0, 3.0, None, 0x10000BB1)],
         0x10000BB2, (-12.0, 6.0)),
        ('a stage-spawned item (no owner anywhere): no target', [(0x20000CCC, 7.0, 0.0, 0x50000000, False)],
         0x20000CCC, None),
        ('an item owned by a gimmick (category 3): no target', [(0x20000CCD, 7.0, 0.0, 0x30000001, False)],
         0x20000CCD, None),
        ('a loop (the shot\'s owner is itself, its link the item, the item\'s owner the shot): no target',
         [(0x10000D01, 7.0, 0.0, 0x10000D01, 0x20000D02), (0x20000D02, 5.0, 0.0, 0x10000D01, None)],
         0x10000D01, None),
        ('a chain longer than %d steps: no target' % C.OWNER_DEPTH,
         [(0x10000E00 + i, 7.0, 0.0, 0x10000E01 + i, None) for i in range(C.OWNER_DEPTH + 1)] +
         [(0x00070012, 1.0, 1.0, None, None)], 0x10000E00, None),
        ('the thrower gone: no target', [(0x20000F01, 7.0, 0.0, 0x00080012, None)], 0x20000F01, None),
        ('ui4: the Killer Eye as the game numbers it (an item: category 4), hit by itself: its +0x34 Donkey Kong',
         [(dk, -30.0, 2.0, None, None), (0x40010000, 15.0, 4.0, dk, None)], 0x40010000, (-30.0, 2.0)),
        ('ui4: its shot (a weapon) -> the Killer Eye (category 4, link 0) -> Donkey Kong (+0x34)',
         [(dk, -30.0, 2.0, None, None), (0x40010001, 15.0, 4.0, dk, None), (0x10000889, 8.0, 4.0, None, 0x40010001)],
         0x10000889, (-30.0, 2.0)),
        ('ui4: an item owned by an object of category 5: no target', [(0x40010002, 7.0, 0.0, 0x50000005, False)],
         0x40010002, None),
    ]
    for what, objs, hit, want_xy in cases:
        e.objects.clear()
        fk = e.fighter(kind, status=C.ST_SS, x=0.0)
        for oid, x, y, owner, link in objs:
            e.obj(oid, x=x, y=y, owner=owner, link=link)
        if 'gone' in what:
            e.obj(0x00080012, x=-3.0, alive=False)
        msg, am, rec = message(e, damage=6.0, category=hit >> 28, oid=hit)
        hitdata(e)
        r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
        want = list(base)
        hx = [o for o in objs if o[0] == hit][0][1]
        if want_xy:
            want[6], want[7], want[8], want[9] = 6.0, (1.0 if want_xy[0] > 0 else -1.0), want_xy[0], want_xy[1]
            fl = F0 | 0x70000
        else:
            want[6], want[7] = 6.0, (1.0 if hx > 0 else -1.0)
            fl = F0 | 0x30000
        check('slot 42 (v4 chain), %s' % what, (e.floats(fk), e.flagw(fk)[0]), (want, fl))
        check('  registers kept', kept, True)


def persist2_checks(e):
    """v4: Mesh_Visibility Persist 2 (mvp2, mesh_vis_cave's mv_apply entered through it)"""
    got = []
    e.stub(C.SETVIS, lambda em: (got.append(tuple(em.r(i) for i in (3, 4, 5, 6))), 1)[1])
    back = []
    e.stub(C.MV_APPLY + 4, lambda em: back.append((em.r(3), em.r(1))))
    mi = e.alloc(0x800, b'\0')
    arr = e.alloc(0x10, b'\0')
    bytes_ = e.alloc(0x40, b'\xFE')
    e.setw(mi + C.MV_ARR, arr)
    e.setw(arr + 4, bytes_)
    for vis, want_v in ((0, 0), (1, 1), (2, 2), (7, 2)):
        prm = e.alloc(0x20, b'\0')
        e.setw(prm + 8, vis)
        e.setw(prm + 0xC, 2)
        got.clear()
        back.clear()
        e.mu.reg_write(REGS[27], mi)
        e.mu.reg_write(REGS[30], prm)
        e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
        e.call(C.MV_APPLY, 9)
        check('Persist 2, Visible %d: the game\'s setter (MI, mesh 9, %d, which 0), no override entry' % (vis, want_v),
              (got, back), ([(mi, 9, want_v, 0)], []))
    for per in (0, 1):
        prm = e.alloc(0x20, b'\0')
        e.setw(prm + 8, 0)
        e.setw(prm + 0xC, per)
        got.clear()
        back.clear()
        e.mu.reg_write(REGS[27], mi)
        e.mu.reg_write(REGS[30], prm)
        e.call(C.MV_APPLY, 9)
        check('Persist %d: mv_apply as before (its first word run, on at +4 with the mesh), no setter call' % per,
              (got, [(m, sp) for m, sp in back]), ([], [(9, 0x700F0000 - 0x20)]))


def diag_checks(path, kind):
    """--diag: the lines (OSReport through the veneer, its arguments)"""
    e = Run(path)
    lines = []

    def osr(em):
        fmt = em.cstr(em.r(3))
        lines.append((fmt.split(' ')[0], tuple(em.r(i) for i in range(4, 11))))
    e.stub(C.OSREPORT_VENEER, osr)
    # slot 42: the Killer Eye's chain
    e.objects.clear()
    dk = 0x00020012
    fk = e.fighter(kind, status=C.ST_SS, x=0.0)
    e.obj(dk, x=-30.0, y=2.0)
    e.obj(0x20000777, x=15.0, y=4.0, owner=dk)
    e.obj(0x10000888, x=8.0, y=4.0, owner=0x20000777)
    msg, am, rec = message(e, damage=6.0, category=1, oid=0x10000888)
    hitdata(e)
    lines.clear()
    r, kept = e.run(C.SLOT42_HOOK, 0, fk['f'], msg)
    want = [('S4U2', (C.ST_SS, 1, 1, 0x10000888, (0x0000C00F | 0x70000), fbits(-30.0), fbits(2.0))),
            ('S4U5', (2, 0x20000777, dk, 0, 0))]
    check('diag S4U2 / S4U5: the status, group, category, object, flags, X / Y; the chain\'s ids',
          [(t, a[:7] if t == 'S4U2' else a[:5]) for t, a in lines], want)
    check('  floats as the release build', e.floats(fk)[6:10], [6.0, -1.0, -30.0, 2.0])
    check('  registers kept', kept, True)
    # slot 42 for Mario (kind 3): no line
    lines.clear()
    fm = e.fighter(3, status=C.ST_SS)
    e.run(C.SLOT42_HOOK, 0, fm['f'], msg)
    check('diag: Mario (kind 3) gets no slot-42 line', lines, [])
    # slot 43 (ui4: the shield damage): S4U3 st, TIMER_0's bits as read (0 when not read), ret
    for status, form, want_ret, mode in ((0, 2000.0, 0, 0.0), (0, 0.0, 1, 0.0), (C.ST_UI, 0.0, 0, C.MODE_FORM)):
        lines.clear()
        r, kept, msg, sk = slot43_case(e, kind, status=status, form=form, mode=mode)
        l43 = [a for t, a in lines if t == 'S4U3']
        check('diag S4U3 st=0x%X TIMER_0 %g: one line (status, TIMER_0 as read, ret %d)' % (status, form, want_ret),
              [a[:3] for a in l43], [(status, fbits(form) if status == 0 else 0, want_ret)])
        check('  slot 43\'s result as the release build\'s', (r, kept), (want_ret, True))
    # ui4: the autododge's S4U2: flags | 0x321 / 0x322 (the timer signalled)
    for ox, low in ((20.0, 0x321), (-20.0, 0x322)):
        lines.clear()
        r, kept, sk, msg, am, hd = dodge42_case(e, kind, status=0, obj_x=ox)
        l42 = [a for t, a in lines if t == 'S4U2']
        check('diag S4U2, the autododge (Wait, the object at %+g): status 0, group 1, category 0, its id, flags | 0x%X'
              % (ox, low), [a[:5] for a in l42], [(0, 1, 0, 0x00030012, 0x0000C00F | low)])
    lines.clear()
    r, kept, sk, msg, am, hd = dodge42_case(e, kind, status=0, form=0.0)
    check('diag S4U2, Wait not transformed: no dodge bits', [a[4] for t, a in lines if t == 'S4U2'], [0x0000C00F])
    # Persist 2: S4UV
    e.stub(C.SETVIS, lambda em: 1)
    mi = e.alloc(0x800, b'\0')
    arr = e.alloc(0x10, b'\0')
    by = e.alloc(0x40, b'\xFE')
    e.setw(mi + C.MV_ARR, arr)
    e.setw(arr + 4, by)
    prm = e.alloc(0x20, b'\0')
    e.setw(prm + 8, 0)
    e.setw(prm + 0xC, 2)
    e.mu.reg_write(REGS[27], mi)
    e.mu.reg_write(REGS[30], prm)
    lines.clear()
    e.call(C.MV_APPLY, 5)
    check('diag S4UV: the instance, mesh, value, the byte before / after', [(t, a[:5]) for t, a in lines],
          [('S4UV', (mi, 5, 0, 0xFE, 0xFE))])
    # the motion -> hash lookup from the motion change (0x027607CC's bl, LR 0x027607D0): S4UM
    tab = e.alloc(0x400, b'\0')
    mt = e.alloc(0x1000, b'\0')
    e.setw(tab, kind)
    e.setw(tab + 8, 600)
    e.setw(tab + 0xC, mt)
    e.setw(mt + 4 * 0x231, 0x9221C757)
    fs = e.fighter(kind, status=C.ST_UI)           # v5: S4UM's status, from 0x027606C0's r27 (the script module)
    smod = e.alloc(0x10, b'\0')
    e.setw(smod + 4, fs['acc'])
    for k, mot, want_n in ((kind, 0x231, 1), (3, 0x231, 0)):
        lines.clear()
        e.mu.reg_write(REGS[27], smod)
        e.mu.reg_write(REGS[3], tab)
        e.mu.reg_write(REGS[4], k)
        e.mu.reg_write(REGS[5], mot)
        e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
        e.mu.emu_start(C.MHASH_FROM - 4, C.MHASH_FROM, count=20000)
        check('diag S4UM: kind 0x%X motion 0x%X: %d line(s), the hash returned, the status (v5)' % (k, mot, want_n),
              ([a[:3] + a[4:5] for t, a in lines if t == 'S4UM'], e.r(3)),
              ([(kind, 0x231, 0x9221C757, C.ST_UI)] * want_n, 0x9221C757 if k == kind else 0))
    # ui4: S4UF (the transformation's motion): bank 0x341's slot, its .efc entry count, its .ptcl resource
    mgr = e.alloc(0xB8 + 0x80 * 8, b'\0')
    efc = e.alloc(0x20, b'\0')
    e.mu.mem_write(efc + 8, struct.pack('>h', 0x6C))
    slot = mgr + 0xB8 + 0x80 * 5
    e.setw(slot + 4, 7)
    e.setw(slot + 8, efc)
    e.setw(C.EFF_MGR, mgr)
    asked = []
    e.stub(C.EFF_SLOT, lambda em: (asked.append((em.r(3), em.r(4), em.r(5))), 5)[1])
    for mot, want_n in ((0x231, 1), (0x245, 1), (0x229, 0)):
        lines.clear()
        asked.clear()
        e.setw(mt + 4 * mot, 0x9221C757)
        e.mu.reg_write(REGS[27], smod)
        e.mu.reg_write(REGS[3], tab)
        e.mu.reg_write(REGS[4], kind)
        e.mu.reg_write(REGS[5], mot)
        e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
        e.mu.emu_start(C.MHASH_FROM - 4, C.MHASH_FROM, count=20000)
        check('ui4 diag S4UF, motion 0x%X: %d line(s): bank 0x341, its slot, the .efc entry count as held, the .ptcl '
              'resource; the slot asked (mgr, 0x341, 0)' % (mot, want_n), ([a[:5] for t, a in lines if t == 'S4UF'],
                                                                         asked),
              ([(0x341, 5, 0x6C, 7, mot)] * want_n, [(mgr, 0x341, 0)] * want_n))
    e.stub(C.EFF_SLOT, lambda em: 0x7F)
    lines.clear()
    e.mu.reg_write(REGS[27], smod)
    e.mu.reg_write(REGS[3], tab)
    e.mu.reg_write(REGS[4], kind)
    e.mu.reg_write(REGS[5], 0x231)
    e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
    e.mu.emu_start(C.MHASH_FROM - 4, C.MHASH_FROM, count=20000)
    check('ui4 diag S4UF, the bank not loaded (slot 0x7F): entries / resource -1', [a[:4] for t, a in lines
                                                                                     if t == 'S4UF'],
          [(0x341, 0x7F, 0xFFFFFFFF, 0xFFFFFFFF)])
    # ui4: the effect runtime's print (0x04A58A8C) to OSReport, capped
    fmt = e.alloc(0x40, b'\0')
    e.mu.mem_write(fmt, b'Emitter is Empty.\n\0')
    got = []
    for k in range(C.EFT_CAP + 2):
        lines.clear()
        for i, v in enumerate((fmt, 11, 12, 13)):
            e.mu.reg_write(REGS[3 + i], v)
        e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
        e.mu.reg_write(UC_PPC_REG_LR, 0x7F000100)
        e.mu.emu_start(C.EFT_PRINT, 0x7F000100, count=20000)
        got.append(len(lines))
    check('ui4 diag: the effect runtime\'s messages through OSReport (format, its arguments), %d lines, then the game\'s '
          'no-op' % C.EFT_CAP, (got[:C.EFT_CAP] == [1] * C.EFT_CAP, got[C.EFT_CAP:]), (True, [0, 0]))
    # v5: S4U4, the frames after a dodge signal (the script module's late update, its call 0x02E4133C)
    late = []
    e.stub(C.LATE_FN, lambda em: late.append(em.r(3)))
    lines.clear()
    r, kept, sk, msg, am, hd = dodge42_case(e, kind, status=0, form=2000.0)
    check('diag: slot 42 signalled a dodge (the S4U4 lines armed)', e.vars.get(C.V_DODGE_R), 4.0)
    att = e.fighter(0x12, status=0x25, x=20.0, slot=1)
    smod = e.alloc(0x10, b'\0')
    e.setw(smod + 4, sk['acc'])
    other = e.alloc(0x10, b'\0')
    e.setw(other + 4, att['acc'])
    got = []
    for k in range(C.DIAG_LATE_N + 2):
        for mod in (other, smod):
            lines.clear()
            e.mu.reg_write(REGS[3], mod)
            e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
            e.mu.emu_start(C.LATE_HOOK, C.LATE_HOOK + 4, count=20000)
            got.append((mod == smod, [a[:5] for t, a in lines if t == 'S4U4'], late[-1] == mod))
    check('diag S4U4: his module only, %d lines (status, TIMER_1 / 2 / 4 bits, lines left), then none; the late update '
          'called on for every object with its module' % C.DIAG_LATE_N, got,
          [(m, [(0, fbits(4.0), fbits(0.0), fbits(0.0), C.DIAG_LATE_N - 1 - k)] if m and k < C.DIAG_LATE_N else [], True)
           for k in range(C.DIAG_LATE_N + 2) for m in (False, True)])
    # the bind's lookup (0x02BEE580's bl) from the motion change: S4UB
    import zlib
    for found, h, want_n in ((0, 'speciallwlight', 1), (-1, 'speciallwlight', 1), (0, 'attack11', 0)):
        e.stub(C.BIND_FN, lambda em, f=found: f & 0xFFFFFFFF)
        lines.clear()
        sp = 0x700F0000
        e.setw(sp + 0x14, C.BIND_FROM)
        e.mu.reg_write(UC_PPC_REG_1, sp)
        e.mu.reg_write(REGS[5], zlib.crc32(h.encode()))
        e.mu.reg_write(REGS[29], 3)
        e.mu.reg_write(REGS[30], kind)
        e.mu.emu_start(C.BIND_HOOK, C.BIND_HOOK + 4, count=20000)
        check('diag S4UB: %s, found %d: %d line(s), the lookup\'s result given back' % (h, found == 0, want_n),
              ([a[:4] for t, a in lines if t == 'S4UB'], e.r(3)),
              ([(zlib.crc32(h.encode()), int(found == 0), 3, kind)] * want_n, found & 0xFFFFFFFF))


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
    event_checks(base)
    e = Run(patched)
    setup_checks(e, kind)
    slot42_checks(e, kind)
    dodge42_checks(e, kind)
    slot43_checks(e, kind)
    chain_checks(e, kind)
    persist2_checks(e)
    diag = a[2] if len(a) > 2 else None
    if diag is None:
        tmp2 = tempfile.TemporaryDirectory()
        diag = os.path.join(tmp2.name, 'diag.rpx')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'rpx_patch.py'), base, diag] + C.args(diag=True),
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
    diag_checks(diag, kind)
    print('%d failure(s)' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
