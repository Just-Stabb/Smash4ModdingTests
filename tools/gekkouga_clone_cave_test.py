#!/usr/bin/env python3
"""Runs tools/gekkouga_clone_cave.py's code in unicorn, in a patched RPX, on the game's own code around it.

  python3 tools/gekkouga_clone_cave_test.py BASE.rpx PATCHED.rpx [--diag]

BASE: the executable the cave was built on (exe_v46z_ui10); PATCHED: BASE + the cave's arguments (exe_v46z_gk1, or the
_diag pair with --diag). Fake fighters / modules in emulator memory; the game functions the cave calls are stubbed
(recording their arguments), the switches / tables it extends are the game's (and the weapon cave's) own code.

Checks:
- words: the patched RPX has every word of the cave; the hooked words in BASE are the game's; no relocation on them;
  the cave space and the trampoline are free in BASE; nothing else differs between BASE and PATCHED;
- the clone weapon kind 0x1A1: the game's weapon descriptor getter (0x0320D934) returns its descriptor (bunshin's
  bytes, its motion info: his 668 body motions' hashes and flags, v2 his parts / groups); the singleton getter (0x03210C30) its own singleton
  whose vtable is bunshin's but +0xAC; the module set-up's row stub gives its own row (bunshin's + the shuriken's
  slots 0 / 2 / 5 / 8 / 9 / 11); the name / static tables (owner "gekkouga", name / folder "clone", bunshin's flags);
  the hit method: result bits 0x1 / 0x2 / 0x4 / 0x10 -> 0 (kept), 0x8 -> bunshin's method; v2: a hit / shield sets
  the owner's VAR_22 (the slot in the clone's VAR_0; not for slot 0 / 9, a dead entry, no accessor);
- his fighter descriptor (the fighter descriptor switch 0x02E4313C, kind 0x30): his descriptor copy, +4 his motion
  info, +8 his 6 articles + the clones (6 / 7: 0x1A1, max 1); every other kind's descriptor as before;
- slot 0's group-1 init: the group init gets our desc (4 capsules on joint 0 at z = -28 / -14 / 14 / 28, y 3-15, r 5.5,
  joint 0, type 2) with the game's other arguments;
- slot 13: VAR_20 bit 1 -> his slot's hide counter = 4 (slot from his table entry; a fighter not in the table: nothing);
  bit 2 -> the Timer's slow once (SlowModule vt +0x44: slot 3, rate 2, 600 frames, owner none), kept while the bit
  holds, cleared (vt +0x6C, slot 3) when it goes; then his slot 13 (the stwu replayed, r3 / r4 / r5 and the stack kept);
- slot 42: group 1 with VAR_20 bit 4 -> VAR_21 = 10000 + (the hitting object's X - his X) (0 when it is gone), no
  vanilla code; group 0, or no clones -> his slot 42 (stwu replayed, registers kept);
- slot 43: VAR_21 > 0.5 -> 0 and the message's handled bit; else his slot 43;
- the HUD hook: a running hide counter -> the cursor at (FAR, FAR), the counter - 1, then 0x03091E34 (r3 the cursor);
  a stopped one: the cursor untouched; player = 8 - r29.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gekkouga_clone_cave as C  # noqa: E402
import kind_expand as K  # noqa: E402
import weapon_expand as W  # noqa: E402
from kind_expand_test import Emu, REGS  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_MSR, UC_PPC_REG_FPR1, UC_PPC_REG_FPR2, UC_PPC_REG_LR  # noqa: E402

fails = 0
checks = 0


def _near(a, b, tol):
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_near(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= tol
    return a == b


def check(what, got, want, tol=None):
    global fails, checks
    checks += 1
    ok = got == want if tol is None else _near(got, want, tol)
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))
    return ok


M1 = 0xFFFFFFFF


def ddiag_rows(e, A):
    """v8: the S4GM (7 values) / S4GN (5) logs"""
    return [x[:8] if x[0] == A['gk_fm'] else x[:6] for x in e.osr_full if x[0] in (A['gk_fm'], A['gk_fn'])]


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
        self.set_wm = []
        self.vars = {}
        self.gone = 0
        self.obj_x = 0.0
        self.pos = self.alloc(0x10, b'\0')
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        self.stub(C.HANDLE, lambda e: e.rec('handle', 3, 4, 5, 6))
        self.stub(C.HANDLE_GONE, lambda e: (e.rec('gone', 3), e.gone)[1])
        self.stub(C.HANDLE_POS, self.pos_fn)
        self.stub(C.G1_FN, lambda e: (e.calls.append(('g1',) + tuple(e.r(i) for i in range(3, 10))), 4)[1])
        self.stub(C.HUD_FN, lambda e: e.rec('hudfn', 3))
        # a WorkModule whose get / set_float are the variables (the user variables' hooks)
        self.wm_vt = self.alloc(0x100, b'\0')
        self.getf, self.setf = self.alloc(4), self.alloc(4)
        self.setw(self.wm_vt + 0x44, self.getf)
        self.setw(self.wm_vt + 0x4C, self.setf)
        self.stub(self.getf, self.getf_fn)
        self.stub(self.setf, self.setf_fn)
        self.slow_vt = self.alloc(0x100, b'\0')
        self.slow_set, self.slow_clr = self.alloc(4), self.alloc(4)
        self.setw(self.slow_vt + 0x44, self.slow_set)
        self.setw(self.slow_vt + 0x6C, self.slow_clr)
        self.stub(self.slow_set, lambda e: e.rec('slow_set', 3, 4, 5, 6, 7, 8))
        self.stub(self.slow_clr, lambda e: e.rec('slow_clr', 3, 4))
        # the fighter table: 8 entries of 0x76B0 (fake objects only where used)
        self.entries = self.alloc(C.ENTRY * 8, b'\0')
        tab = self.alloc(0x20, b'\0')
        self.setw(tab, self.entries)
        self.setw(tab + 8, 8)
        holder = self.alloc(0x10, b'\0')
        self.setw(holder, tab)
        self.setw(C.FIGHTERS, holder)

    def rec(self, name, *regs):
        self.calls.append((name,) + tuple(self.r(i) for i in regs))

    def pos_fn(self, e):
        self.rec('pos', 3)
        self.mu.mem_write(self.pos, struct.pack('>f', self.obj_x))
        return self.pos

    def getf_fn(self, e):
        self.calls.append(('getf', self.r(4)))
        self.mu.reg_write(UC_PPC_REG_FPR1, f2d(self.vars.get(self.r(4), 0.0)))

    def setf_fn(self, e):
        v = round(d2f(self.mu.reg_read(UC_PPC_REG_FPR1)), 3)
        self.calls.append(('setf', self.r(4), v))
        self.set_wm.append(self.r(3))
        self.vars[self.r(4)] = v

    def fighter(self, slot, x=5.0):
        """his table entry (slot) and module block: WorkModule (variables), PostureModule (+0x10 x), the accessor's
        SlowModule ([entry + 0xC] + 0xB8)"""
        f = self.entries + C.ENTRY * slot if slot is not None else self.alloc(0x100, b'\0')
        blk = self.alloc(0x7400, b'\0')
        self.setw(f + 4, C.GK_KIND)
        self.setw(f + C.ACC, blk)
        wm = self.alloc(0x20, b'\0')
        self.setw(wm, self.wm_vt)
        self.setw(blk + C.WORK, wm)
        posture = self.alloc(0x40, b'\0')
        self.mu.mem_write(posture + 0x10, struct.pack('>f', x))
        self.setw(blk + C.POSTURE, posture)
        acc = self.alloc(0x100, b'\0')
        slow = self.alloc(0x20, b'\0')
        self.setw(slow, self.slow_vt)
        self.setw(acc + 0xB8, slow)
        self.setw(f + C.BASE_ACC, acc)
        return dict(f=f, blk=blk, wm=wm, slow=slow)

    def run_to(self, fn, until, *args):
        """run fn until `until` (the original slot's second word): r1 there, the registers"""
        for i in range(14, 32):
            self.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        self.mu.reg_write(UC_PPC_REG_MSR, self.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        return self.call(fn, *args, until=until)

    def kept(self):
        return all(self.r(i) == 0x5A5A0000 + i for i in range(14, 32))


def words_checks(base, patched, diag, feats=None):
    out, info = C.build(base, diag, feats)
    img, pimg = K.Image(base), K.Image(patched)
    check('the patched RPX has every word', [hex(a) for a, (w, _n) in sorted(out.words.items()) if pimg.w(a) != w][:4], [])
    check('the hooked words in the base are the game\'s', [hex(a) for a, w in C.ORIGINAL.items() if img.w(a) != w], [])
    check('no relocation on a hooked word', [hex(a) for a in C.ORIGINAL if a in img.relocs()], [])
    check('the cave space is past the base\'s text', img.text_end() <= C.CAVE, True)
    check('the trampoline words are zero in the base', [img.w(C.TRAMP + 4 * i) for i in range(4)], [0, 0, 0, 0])
    diff = []
    for base_, data in img.mem:
        for o in range(0, len(data), 4):
            a = base_ + o
            if a in out.words:
                continue
            try:
                if pimg.w(a) != struct.unpack('>I', data[o:o + 4])[0]:
                    diff.append(hex(a))
            except KeyError:
                pass
            if len(diff) > 3:
                break
    check('nothing else differs from the base', diff, [])
    return out, info


def weapon_checks(e, img, info, diag=False):
    L, A, lab = info['layout'], info['A'], info['labels']
    d = e.call(W.DESC_SWITCH, 0, C.CLONE_KIND)
    check('the weapon descriptor getter: kind 0x1A1 -> its descriptor', d, A['w_desc'])
    check('its bytes: bunshin\'s but +8 (its motion info)',
          [e.w(d + 4 * i) for i in range(L['dsize'] // 4) if i != 2],
          [img.w(L['bdesc'] + 4 * i) for i in range(L['dsize'] // 4) if i != 2])
    mi = e.w(d + 8)
    check('its motion info: his 668 motions', (mi, e.w(mi + 4)), (A['w_minfo'], 668))
    ents = e.w(mi)
    F = info['feats']
    check('the entries: his body motions\' hashes and flags (v2: his fighter motion table\'s entries; v4: flags 0 without '
          '"parts")', [(e.w(ents + 8 * i), e.w(ents + 8 * i + 4)) for i in range(668)],
          L['ents'] if 'parts' in F else [(h, 0) for h, _f in L['ents']])
    his = img.w(C.GK_DESC + 4)
    check('his motion table: 668 entries, hashes the v1 list', ([h for h, _f in L['ents']] == L['hashes'], len(L['ents'])),
          (True, 668))
    check('v2: its motion info\'s words 2-5 are his (parts 0x10378F70 x 6, groups 0x10378FA0 x 5); v4 without "parts": '
          'bunshin\'s (0)', [e.w(mi + 4 * i) for i in range(2, 6)],
          [img.w(his + 4 * i) if 'parts' in F else img.w(L['bminfo'] + 4 * i) for i in range(2, 6)])
    check('... his parts as read: 0x10378F70 6 0x10378FA0 5', [img.w(his + 4 * i) for i in range(2, 6)],
          [0x10378F70, 6, 0x10378FA0, 5])
    check('... each part a 668-word hash table (motion kind -> the part\'s animation; hands 4 / 3, parts 6 / 7 / 8)',
          [(img.w(0x10378F70 + 8 * i + 4), img.w(0x10378F70 + 8 * (i + 1)) - img.w(0x10378F70 + 8 * i))
           for i in range(4)], [(4, 668 * 4), (3, 668 * 4), (6, 668 * 4), (7, 668 * 4)])
    check('its words 6 / 7 bunshin\'s (-90.0 / 90.0)', [e.w(mi + 4 * i) for i in range(6, 8)],
          [img.w(L['bminfo'] + 4 * i) for i in range(6, 8)])
    check('bunshin\'s descriptor unchanged', e.call(W.DESC_SWITCH, 0, C.CLONE_BASE), L['bdesc'])
    s = e.call(W.SINGLETON_SWITCH, 0, C.CLONE_KIND)
    check('the singleton getter: kind 0x1A1 -> its own singleton', s, A['w_single'])
    vt = e.w(s)
    VT_OURS = (W.HIT_METHOD, 0x34) + ((0x1C,) if 'hurt' in F or diag else ()) + (
        C.POLL_SLOTS if F & {'hurt', 'pose'} or diag else (0x94,) if F & {'sway', 'hitcheck', 'burn'} else ())
    check('its vtable: bunshin\'s but +0x1C / +0x64 / +0x84 / +0x8C / +0x94 / +0xAC (v3)',
          [e.w(vt + o) for o in range(0, L['vsize'], 4) if o not in VT_OURS],
          [img.w(L['svt'] + o) for o in range(0, L['vsize'], 4) if o not in VT_OURS])
    check('its +0xAC: the hit method, +0x1C the set-up, the 4 phases\' pollers (v4: by the build\'s features)',
          [e.w(vt + o) for o in VT_OURS],
          [lab['w_hit'], lab['w_start']] + ([lab['w_init']] if 0x1C in VT_OURS else []) +
          [lab['wp_%X' % o] for o in VT_OURS if o in C.POLL_SLOTS])
    check('v6 / v7: its specializer is the moon\'s copy, its +0x34 ours: neither bunshin\'s 0x02AF6738 (black) nor the moon\'s '
          '(the init\'s scale: the user\'s v6 invisible clones)', (e.w(vt + 0x34) != 0x02AF6738,
                                                                  e.w(vt + 0x34) != img.w(W.singleton_of(img, C.VT_BASE)[1] + 0x34)),
          (True, True))
    hits = []
    e.stub(L['old_hit'], lambda e_: e_.rec('base_hit', 3, 4, 5))
    # a clone: weapon +0x28 its accessor: +0x28 WorkModule (VAR_0 its owner's slot, VAR_1 its id), +0x50 AttackModule
    # (hit records), +0x54 DamageModule (vt +0x7C damage this frame), +0x58 HitModule (vt +0x4C hurtboxes)
    cvt = e.alloc(0x100, b'\0')
    cget = e.alloc(4)
    e.setw(cvt + 0x44, cget)
    e.clone_vars = {C.VAR_SLOT: 3.0, C.VAR_ID: 2.0}

    def cget_fn(e_):
        e_.calls.append(('clone_getf', e_.r(4)))
        e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(e_.clone_vars.get(e_.r(4), 0.0)))
    e.stub(cget, cget_fn)
    cset = e.alloc(4)
    e.setw(cvt + 0x4C, cset)

    def cset_fn(e_):
        v = round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)
        e_.calls.append(('clone_setf', e_.r(4), v))
        e_.clone_vars[e_.r(4)] = v
    e.stub(cset, cset_fn)
    cwm = e.alloc(0x10, b'\0')
    e.setw(cwm, cvt)
    cacc = e.alloc(0x100, b'\0')
    e.setw(cacc + C.W_WORK, cwm)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, cacc)
    # its AttackModule: 3 record arrays (hitboxes 0-2), slots of 0x84 (+0x18 damage)
    am = e.alloc(0x60, b'\0')
    arr = e.alloc(0x174 * 3, b'\0')
    slots = e.alloc(0x84 * 3, b'\0')
    e.setw(am + 0x14, arr)
    e.setw(am + 0x18, 3)
    e.setw(am + 0x40, slots)
    for i, dmg in enumerate((8.0, 5.0, 13.0)):
        e.mu.mem_write(slots + 0x84 * i + 0x18, struct.pack('>f', dmg))
    nodes = e.alloc(0x40 * 4, b'\0')

    def records(spec):
        """spec: {hitbox: [ids of its nodes]}; empty lists point at their sentinel"""
        k = 0
        for h in range(3):
            base = arr + 0x174 * h
            prev = base + 0x124
            ids = spec.get(h, [])
            e.setw(base + 0x128, base + 0x124)
            first = None
            for j, hid in enumerate(ids):
                n = nodes + 0x40 * k
                k += 1
                e.mu.mem_write(n + 0x27, bytes([hid]))
                e.setw(n + 4, base + 0x124)
                if first is None:
                    first = n
                else:
                    e.setw(prev + 4, n)
                prev = n
            if first is not None:
                e.setw(base + 0x128, first)
    records({})
    e.setw(cacc + C.W_ATTACK, am)
    e.hs_ret = 7

    def hs_fn(e_):
        e_.calls.append(('hitstop', e_.r(3), e_.r(4), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3),
                         round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR2)), 3), e_.r(5), e_.r(6)))
        return e_.hs_ret
    e.stub(C.HITSTOP_FN, hs_fn)
    owner = e.fighter(2)
    oacc = e.w(owner['f'] + C.BASE_ACC)
    smvt = e.alloc(0x100, b'\0')
    smset = e.alloc(4)
    e.setw(smvt + 0x8C, smset)
    e.stub(smset, lambda e_: e_.rec('stop', 4, 5))
    sm = e.alloc(0x20, b'\0')
    e.setw(sm, smvt)
    e.setw(oacc + C.W_STOP, sm)
    e.mu.mem_write(owner['f'] + 0x1E, b'\x04')
    for bits in (0x1, 0x2, 0x4, 0x10, 0x13, 0x8):
        e.calls, e.set_wm = [], []
        r = e.call(lab['w_hit'], s, weapon, bits)
        hits.append((bits, r if not [c for c in e.calls if c[0] == 'base_hit'] else 'base'))
    check('the hit method: 0x1 / 0x2 / 0x4 / 0x10 kept (0), 0x8 bunshin\'s',
          hits, [(1, 0), (2, 0), (4, 0), (0x10, 0), (0x13, 0), (8, 'base')])

    def landed(slot_var, live=4, bits=0x13, spec=None):
        e.clone_vars[C.VAR_SLOT] = slot_var
        records(spec or {})
        e.mu.mem_write(owner['f'] + 0x1E, bytes([live]))
        e.calls, e.set_wm, e.vars = [], [], {}
        for i in range(14, 32):
            e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        r = e.call(lab['w_hit'], s, weapon, bits)
        return r, [c for c in e.calls if c[0] in ('clone_getf', 'setf', 'hitstop', 'stop')], e.set_wm, e.kept()
    two = {0: [0], 1: [], 2: [2, 2]}
    r = landed(3.0, spec=two)
    want = [('clone_getf', C.VAR_SLOT), ('hitstop', oacc, slots + 0x84 * 2, 13.0, 1.0, 1, 1), ('stop', 7, 1),
            ('setf', C.VAR_LAG, 1.0)]
    check('v3: a landed hit (0x13): the clone\'s VAR_0 (slot 3); its hitbox with the most damage among those with hit '
          'records (id 2, 13%%); the game\'s hitstop for it on HIS accessor (attacker side 1, its own multiplier, x1.0); '
          'his StopModule vt +0x8C(7, 1); VAR_22 = 1.0 through his WorkModule; 0; the registers kept',
          r, (0, want, [owner['wm']], True))
    check('v3: shielded (0x4): the same', landed(3.0, bits=0x4, spec=two)[1], want)
    e.hs_ret = 0
    check('v3: the game\'s hitstop 0 (a no-hitlag hitbox): no stop, VAR_22 still set', landed(3.0, spec=two)[1],
          [want[0], want[1], want[3]])
    e.hs_ret = 7
    check('v3: no hit records: no hitstop call, VAR_22 set (his MSC\'s fallback)', landed(3.0)[1], [want[0], want[3]])
    check('v3: only hitbox 0\'s record: its data (8%%)', landed(3.0, spec={0: [0]})[1][1],
          ('hitstop', oacc, slots, 8.0, 1.0, 1, 1))
    check('v2: slot 0 (its MSC not run yet): nothing set', landed(0.0, spec=two)[1], [('clone_getf', C.VAR_SLOT)])
    check('v2: slot 9: nothing set', landed(9.0, spec=two)[1], [('clone_getf', C.VAR_SLOT)])
    check('v2: the owner\'s entry not live (+0x1E < 4): nothing set', landed(3.0, live=2, spec=two)[1],
          [('clone_getf', C.VAR_SLOT)])
    e.setw(weapon + C.W_ACC, 0)
    check('v2: no accessor: nothing read, 0', landed(3.0)[:2], (0, []))
    e.setw(weapon + C.W_ACC, cacc)
    # ---- v3: the set-up: his hurtboxes on its HitModule
    hmvt = e.alloc(0x100, b'\0')
    hmset = e.alloc(4)
    e.setw(hmvt + 0x4C, hmset)

    def hm_fn(e_):
        d = e_.r(4)
        e_.calls.append(('hurt', e_.r(3), e_.w(d), e_.w(d + 4), e_.r(5)))
        e_.setw(e_.r(3) + C.HM_COUNT, e_.w(e_.r(3) + C.HM_COUNT) + e_.w(d + 4))
    e.stub(hmset, hm_fn)
    hmclr = e.alloc(4)
    e.setw(hmvt + C.HM_CLEAR, hmclr)

    def hm_clear(e_):
        e_.calls.append(('hurt_clear', e_.r(3)))
        e_.setw(e_.r(3) + C.HM_COUNT, 0)
    e.stub(hmclr, hm_clear)
    # v9: a HitModule as the generic weapon params make it: 1 group (records 0-7 after the set-up), 8 objects
    hm = e.alloc(0x80, b'\0')
    e.setw(hm, hmvt)
    hgrp = e.alloc(0x38, b'\0')
    e.mu.mem_write(hgrp + 4, struct.pack('>hh', 0, 8))
    e.setw(hm + C.HM_GROUPS, 1)
    e.setw(hm + C.HM_GROUP, hgrp)
    hrecs = e.alloc(0x40 * 8, b'\0')
    e.mu.mem_write(hrecs, struct.pack('>4I', 0x11, 0x22, 0x33, 0x44))
    e.setw(hm + 0x44, 0x14)                                  # v10: as the game's: +0x44 the capacity (v9 read it as
    e.setw(hm + C.HM_RECS, hrecs)                            # the pointer: the user's C_hurt crash), +0x48 the records
    e.setw(hm + C.HM_OBJS, 8)
    e.setw(cacc + C.W_HIT_MOD, hm)
    e.calls = []
    e.call(lab['w_init'], s, weapon)
    check('v3 set-up (+0x1C): HitModule vt +0x4C(&{his 8 hurtboxes, 8}, 0) (v4: only with "hurt")',
          [c for c in e.calls if c[0] == 'hurt'], [('hurt', hm, A['hurt'], 8, 0)] if 'hurt' in F else [])
    if diag:
        e.osr_full = []
        osr_ = [c for c in e.calls if c[0] == 'osr']
        check('v3 / v4 diag: S4GI clone set-up logged with its HitModule (before the hurtboxes), then S4GJ done',
              ([c[1] for c in osr_], osr_[0][2]), ([A['gk_fi'], A['gk_fj']], hm))
    check('... the hurtbox data: his vl group 5 entries, bones 0x7D0 + his joint, pool 2',
          bytes(e.mu.mem_read(A['hurt'], 0x30 * 8)) == C.hurt_blob() and
          [struct.unpack_from('>I', C.hurt_blob(), 0x30 * i + 0x1C)[0] for i in range(8)] ==
          [0x7D0 + j for j in (12, 19, 22, 16, 8, 4, 9, 5)], True)
    check('v7: its +0x34 (the start) is ours', e.w(vt + 0x34), lab['w_start'])
    init = e.alloc(0x80, b'\0')
    e.mu.mem_write(init + 0x68, struct.pack('>f', 2.76))
    # v8: its ColorBlendModule (accessor +0x38): vt +0x44 (slot off)
    cbvt = e.alloc(0x100, b'\0')
    cboff = e.alloc(4)
    e.setw(cbvt + C.COLOUR_CLEAR, cboff)
    e.stub(cboff, lambda e_: e_.rec('colour_off', 3, 4))
    cb = e.alloc(0x100, b'\0')
    e.setw(cb, cbvt)
    e.setw(cacc + C.W_COLOUR, cb)
    e.stub(C.BUNSHIN_START, lambda e_: e_.rec('bunshin_start', 3, 4, 5))
    e.calls = []
    e.setw(hm + C.HM_COUNT, 8)
    e.call(lab['w_start'], s, weapon, init)
    want = ([('clone_setf', C.VAR_LATCH, 0.0)] if 'hitcheck' in F else []) + \
        ([('clone_setf', C.VAR_BIND, 0.0), ('clone_setf', C.VAR_SWAYLOG, 0.0)] if 'sway' in F else []) + \
        ([('bunshin_start', s, weapon, init), ('colour_off', cb, 0)] if 'bstart' in F else []) + \
        ([('hurt_clear', hm), ('hurt', hm, A['hurt'], 8, 0)] if 'hurt' in F else []) + \
        ([('osr', A['gk_fk'], hm, 1), ('osr', A['gk_fy'], 0, 0)] if diag and 'hurt' in F else []) + \
        ([('osr', A['gk_fz'], init, 276)] if diag else [])
    if 'hurt' in F:
        check('v9 "hurt": the start (each time a clone is made) clears its hurtboxes and adds his 8 again: 8 after, '
              'not 16 (v8\'s, made only at the set-up, were never hit)', e.w(hm + C.HM_COUNT), 8)
        if diag:
            check('v9 diag: S4GK (HitModule, groups 1, boxes 8 -> 8, group 0 = records 0 + 8, 8 objects)',
                  [x[:8] for x in e.osr_full if x[0] == A['gk_fk']], [(A['gk_fk'], hm, 1, 8, 8, 0, 8, 8)])
    check('v8: ... ' + ('"bstart": bunshin\'s start (as it is), then its black off (ColorBlendModule vt +0x44(0))'
                        if 'bstart' in F else '"hurt": its hurtboxes again' if 'hurt' in F else 'it calls nothing (v7)') + (', the S4GZ log (init, scale x100 276)' if diag else ''),
          [c[:4] if c[0] == 'osr' else c for c in e.calls], want)
    if diag:
        # v8 diag: the draw state (S4GM / S4GN)
        visvt = e.alloc(0x100, b'\0')
        isvis = e.alloc(4)
        e.setw(visvt + 0xA4, isvis)
        e.stub(isvis, lambda e_: (e_.rec('is_visible', 3), 0x101)[1])
        vis = e.alloc(0x20, b'\0')
        e.setw(vis, visvt)
        e.mu.mem_write(vis + 8, b'\x00')
        e.setw(cacc + C.W_VIS, vis)
        mm = e.alloc(0x20, b'\0')
        mi = e.alloc(0x800, b'\0')
        e.setw(mm + 8, 3)
        e.setw(mm + 0xC, mi)
        e.mu.mem_write(mi + 0x7DB, b'\x01')
        e.setw(cacc + C.W_MODEL, mm)
        e.mu.mem_write(cb + 0x50, b'\x01')
        e.mu.mem_write(cb + 0xD9, b'\x01')
        post = e.alloc(0x80, b'\0')
        e.mu.mem_write(post + 0x18, struct.pack('>f', -12.0))
        e.mu.mem_write(post + 0x5C, struct.pack('>f', 1.25))
        e.setw(cacc + C.W_POSTURE, post)
        lm = e.alloc(0x100, b'\0')
        e.setw(lm + 0x84, 0x80)
        e.setw(cacc + C.W_LINK, lm)
        e.calls, e.osr_full = [], []
        e.call(lab['w_ddiag'], cacc, 2)
        check('v8 diag: w_ddiag: S4GM (id 2, VisibilityModule +8 0, is_visible 1 (its byte), model mode 3, drawn 1, '
              'overlay slot 0 on / enabled) and S4GN (z -12, scale x100 125, link mask 0x80, the ModelModule)',
              ([c for c in e.calls if c[0] == 'is_visible'], ddiag_rows(e, A)),
              ([('is_visible', vis)], [(A['gk_fm'], 2, 0, 1, 3, 1, 1, 1), (A['gk_fn'], 2, -12 & 0xFFFFFFFF, 125, 0x80, mm)]))
        check('v9 diag: S4GO (id 2, its hurtboxes 8, 8 objects, the first record\'s words; none without a HitModule)',
              [x[:8] for x in e.osr_full if x[0] == A['gk_fo']],
              [(A['gk_fo'], 2, 8, 8, 0x11, 0x22, 0x33, 0x44)] if 'hurt' in F else [])
        if 'hurt' in F:
            e.setw(hm + C.HM_RECS, 0x14)
            e.calls, e.osr_full = [], []
            e.call(lab['w_ddiag'], cacc, 2)
            check('v10 diag: a records word outside the data range (v9 dereferenced 0x14: the user\'s C_hurt crash, '
                  'IP 0x04BED250): S4GO with zero words, no read through it',
                  [x[:8] for x in e.osr_full if x[0] == A['gk_fo']], [(A['gk_fo'], 2, 8, 8, 0, 0, 0, 0)])
            e.setw(hm + C.HM_RECS, hrecs)
        for o in (C.W_VIS, C.W_MODEL, C.W_POSTURE, C.W_LINK):
            e.setw(cacc + o, 0)
        e.calls, e.osr_full = [], []
        e.call(lab['w_ddiag'], cacc, 1)
        check('v8 diag: ... modules missing: -1 for each (nothing read through them)',
              ddiag_rows(e, A), [(A['gk_fm'], 1, M1, M1, M1, M1, 1, 1), (A['gk_fn'], 1, M1, M1, M1, 0)])
        e.setw(cacc + C.W_POSTURE, post)
        e.setw(cacc + C.W_VIS, vis)
        e.setw(cacc + C.W_MODEL, mm)
        e.setw(cacc + C.W_LINK, lm)
    # ---- v3: the pollers: the damage this frame -> his VAR_21 = 20000 + its id; then bunshin's method
    dmvt = e.alloc(0x100, b'\0')
    dmget = e.alloc(4)
    e.setw(dmvt + 0x7C, dmget)
    e.dmg = 0.0

    def dm_fn(e_):
        e_.calls.append(('dmg', e_.r(4)))
        e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(e_.dmg))
    e.stub(dmget, dm_fn)
    dm = e.alloc(0x20, b'\0')
    e.setw(dm, dmvt)
    e.setw(cacc + C.W_DAMAGE, dm)
    for o in C.POLL_SLOTS:
        e.stub(L['vt_orig'][o], lambda e_, o=o: e_.rec('orig%X' % o, 3, 4, 5, 6))

    def poll(o, dmg):
        e.dmg = dmg
        e.calls, e.set_wm, e.vars = [], [], {}
        for i in range(14, 32):
            e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        e.call(lab['wp_%X' % o], s, weapon, 0x55, 0x66)
        e.osr_seen = [c for c in e.calls if c[0] == 'osr']
        return [c for c in e.calls if c[0] in ('dmg', 'setf') or c[0].startswith('orig')], e.set_wm, e.kept()
    e.mu.mem_write(owner['f'] + 0x1E, b'\x04')
    e.clone_vars[C.VAR_SLOT] = 3.0
    e.clone_vars[C.VAR_LOGGED] = 0.0
    if diag:
        e.clone_vars[C.VAR_ID] = 0.0
        poll(0x64, 0.0)
        check('v4 diag: the clone\'s first update logs S4GP (its accessor) before its script names it',
              ([c[1:3] for c in e.osr_seen], e.clone_vars.get(C.VAR_LOGGED)), ([(A['gk_fp'], cacc)], 0.5))
        poll(0x64, 0.0)
        check('v4 diag: ... not again (still unnamed)', e.osr_seen, [])
        e.clone_vars[C.VAR_ID] = 2.0
        poll(0x64, 0.0)
        check('v3 diag: named: S4GC (id 2, owner slot 3) once, its VAR_2 1',
              ([c[1:3] + (c[3],) for c in e.osr_seen], e.clone_vars.get(C.VAR_LOGGED)), ([(A['gk_fc'], 2, 3)], 1.0))
        poll(0x64, 0.0)
        check('v3 diag: ... not again; v8: its 4th poll (its first frame) logs its place and draw state (S4GX, S4GM, S4GN)',
              [c[1] for c in e.osr_seen], [A['gk_fx'], A['gk_fm'], A['gk_fn'], A['gk_fq']] + ([A['gk_fo']] if 'hurt' in F else []))
        poll(0x64, 0.0)
        check('v8 diag: ... then nothing until its 120th poll', e.osr_seen, [])
    if 'hurt' not in F:
        if diag:
            check('v4 without "poll": the pollers never read the DamageModule, bunshin\'s methods still run',
                  poll(0x64, 3.5)[0], [('orig64', s, weapon, 0x55, 0x66)])
        POLLS = ()
    else:
        POLLS = C.POLL_SLOTS
    for o in POLLS:
        check('v3 poller +0x%X, no damage: nothing set, bunshin\'s method with the same arguments' % o, poll(o, 0.0),
              ([('dmg', 0), ('orig%X' % o, s, weapon, 0x55, 0x66)], [], True))
    if POLLS:
        check('v3 poller +0x64, 3.5 damage this frame: his VAR_21 = 20000 + its id (2) through his WorkModule, then bunshin\'s',
              poll(0x64, 3.5), ([('dmg', 0), ('setf', C.VAR_HIT, 20002.0), ('orig64', s, weapon, 0x55, 0x66)], [owner['wm']], True))
        e.clone_vars[C.VAR_ID] = 1.0
        check('v3 poller +0x8C, the left clone (id 1)', poll(0x8C, 1.0)[0][1], ('setf', C.VAR_HIT, 20001.0))
        e.clone_vars[C.VAR_SLOT] = 0.0
        check('v3 poller: slot 0: nothing set', poll(0x94, 2.0)[0], [('dmg', 0), ('orig94', s, weapon, 0x55, 0x66)])
    e.mu.mem_write(owner['f'] + 0x1E, b'\x00')
    # the module row stub (the bl at MODULE_ROW): r30 = kind -> r8 = row - MODULE_TABLE
    mr = K.branch_target(W.MODULE_ROW, img.w(W.MODULE_ROW))
    e.mu.reg_write(REGS[30], C.CLONE_KIND)
    e.call(mr)
    row = (e.r(8) + W.MODULE_TABLE) & 0xFFFFFFFF
    check('the module set-up: kind 0x1A1 -> its own row', row, A['w_row'])
    tk = C.base_of(F)
    want = C.row_of(img, F)
    dummy = lambda f: img.w(f) == 0x38600000 and img.w(f + 4) == 0x4E800020
    check('v5: the row has the MSC agent (slot 8, moon\'s / the pump\'s constructor %08X) and the base kind\'s template updates '
          'it (+0x1C)' % want[C.MSC_SLOT], (not dummy(want[C.MSC_SLOT]), want[C.MSC_SLOT] == img.w(W.MODULE_TABLE + 0x70 * 0xFC + 4 * 8)),
          (True, True))
    check('v5: attack: the AttackModule (slot 2); hurt: Hit (6) and Damage (20); safe: neither',
          (not dummy(want[2]), not dummy(want[6]), not dummy(want[20])),
          ('attack' in F or 'hurt' in F, 'hurt' in F, 'hurt' in F))
    check('v3 / v5: its row: the feature set\'s (safe: bunshin + moon\'s MSC agent; attack: + the pump\'s; hurt: mewtwom\'s + Damage)',
          [e.w(row + 4 * j) for j in range(28)], want)
    T_ = info['T']
    check('v5: its base kind (the weapon switches\' templates): moon 0xFC / the pump 0x2 / mewtwom 0x168',
          e.w(T_['bt'] + 4 * (C.CLONE_KIND - W.OLD_N)), tk)
    nt = dict(W.NAME_TABLES)
    check('v5: the base kinds are his moon, Mario\'s pump, Mewtwo\'s mewtwom (the u16 flags: model, no category bits for '
          'moon\'s / pump\'s 0x871 / 0x87C)', [(img.cstr(img.w(nt['owner'] + 4 * k)), img.cstr(img.w(nt['name'] + 4 * k)))
                                             for k in (C.SAFE_BASE, C.ATTACK_BASE, C.HURT_BASE)],
          [('gekkouga', 'moon'), ('mario', 'pump'), ('mewtwo', 'mewtwom')])
    e.mu.reg_write(REGS[30], CLONE_OTHER)
    e.call(mr)
    check('the module set-up: bunshin\'s own row as before', e.r(8), 0x70 * CLONE_OTHER)
    T = info['T']
    check('owner "gekkouga", name / folder "clone"',
          [e.cstr(e.w(T[n] + 4 * C.CLONE_KIND)) for n in ('owner', 'name', 'folder')], ['gekkouga', 'clone', 'clone'])
    check('root and static tables: bunshin\'s (v3: the u16 flags without the category bits)',
          (e.w(T['root'] + 4 * C.CLONE_KIND), e.w(T['u32'] + 4 * C.CLONE_KIND),
           struct.unpack('>H', bytes(e.mu.mem_read(T['u16'] + 2 * C.CLONE_KIND, 2)))[0],
           bytes(e.mu.mem_read(T['u8'] + C.CLONE_KIND, 1))[0]),
          (img.w(W.NAME_TABLES[0][1] + 4 * C.CLONE_BASE), img.w(W.STATIC_TABLES[0][1] + 4 * C.CLONE_BASE),
           img.h(W.STATIC_TABLES[2][1] + 2 * C.CLONE_BASE) & ~C.CATEGORY_BITS, img.b(W.STATIC_TABLES[1][1] + C.CLONE_BASE)))
    u16 = struct.unpack('>H', bytes(e.mu.mem_read(T['u16'] + 2 * C.CLONE_KIND, 2)))[0]
    check('v3: the clone\'s u16 flags 0x87C: no resource category bit (0x80 / 0x1 / 0x100), so its files load with him '
          '(bunshin\'s 0x87D has 0x1: the Final Smash load, why v1 / v2\'s clones never appeared)', (hex(u16), u16 & 0x181), ('0x87c', 0))
    check('the u16 flags have a model (0x40) in the owner\'s colour (0x10)', img.h(W.STATIC_TABLES[2][1] + 2 * C.CLONE_BASE) & 0x50, 0x50)


CLONE_OTHER = 0xFE


def fighter_desc_checks(e, img, info):
    A = info['A']
    fd = 0x02E4313C                     # the fighter descriptor switch (its prologue: mflr / stw / stwu)
    d = e.call(fd, 0, C.GK_KIND)
    check('his fighter descriptor: the copy', d, A['gk_desc'])
    check('its bytes: his, +8 the new list', [e.w(d + 4 * i) for i in range(14) if i != 2],
          [img.w(C.GK_DESC + 4 * i) for i in range(14) if i != 2])
    al = e.w(d + 8)
    ents, n = e.w(al), e.w(al + 4)
    rows = [[e.w(ents + 16 * i + 4 * j) for j in range(4)] for i in range(n)]
    van = img.w(C.GK_DESC + 8)
    vrows = [[img.w(img.w(van) + 16 * i + 4 * j) for j in range(4)] for i in range(6)]
    cart = 'cart' in info['feats']
    ice = 'ice' in info['feats']
    trn = C.TR_MAX + (C.ICE_SLOTS_EXTRA if ice else 0)
    if cart:
        vrows[0] = [vrows[0][0], C.SH_MAX] + vrows[0][2:]
    check('his articles 0-5 as before%s, 6 / 7 the clones (0x1A1, max 1, no spawner)%s%s' % (
          ' (clone articles v1: 9 shurikens, his and his clones\')' if cart else '',
          ', 8 the skeleton' if 'skeleton' in info['feats'] else '',
          ', 9 the fire trails (burn v2: 0x1A3, %d at once%s)' % (trn, ' (ice detonation v1: + 2 for blasts)' if ice else '')
          if 'burn2' in info['feats'] else '') + (', 10 the Parabeetle (parabeetle v1: 0x1A4, 3 at once)'
                                                   if 'pbeetle' in info['feats'] else ''), rows,
          vrows + [[C.CLONE_KIND, 1, 0, 0], [C.CLONE_KIND, 1, 0, 0]] +
          ([[C.SK_KIND, C.SK_LEVELS if cart else 1, 0, 0]] if 'skeleton' in info['feats'] else []) +
          ([[C.TR_KIND, trn, 0, 0]] if 'burn2' in info['feats'] else []) +
          ([[C.PB_KIND, C.PB_MAX, 0, 0]] if 'pbeetle' in info['feats'] else []))
    check('the article instances in all (the ArticleModule holder\'s 64: docs/native-notes.md "Article instance cap")',
          sum(r[1] for r in rows) <= 64, True)
    others = []
    for k in (0x3, 0x10, 0x2F, 0x31, 0x41, 0x47):
        try:
            others.append(e.call(fd, 0, k) != A['gk_desc'])
        except Exception:
            others.append('err')
    check('other kinds: not his copy', others, [True] * 6)


def g1_checks(e, info):
    e.calls = []
    e.call(info['labels']['g1_stub'], 0x11, 0x22, 0x33, 0x44, 0xDEAD, 1, 0x77)
    c = [x for x in e.calls if x[0] == 'g1']
    check('slot 0: the group init once, r7 our desc, the game\'s other arguments',
          [(x[1], x[2], x[3], x[4], x[5], x[6], x[7]) for x in c], [(0x11, 0x22, 0x33, 0x44, info['A']['g1_desc'], 1, 0x77)])
    d = info['A']['g1_desc']
    check('the desc: {shapes, 4, bytes 0 0 0 1}', (e.w(d), e.w(d + 4), e.w(d + 8)), (info['A']['g1_shapes'], 4, 1))
    shapes = []
    for i in range(4):
        b = bytes(e.mu.mem_read(e.w(d) + 0x20 * i, 0x20))
        f = struct.unpack('>7f', b[:28])
        shapes.append(tuple(round(v, 2) for v in f) + (struct.unpack('>H', b[28:30])[0], b[30]))
    check('the shapes: capsules on joint 0 at the clone places', shapes,
          [(0.0, 3.0, z, 0.0, 15.0, z, 5.5, 0, 2) for z in (-28.0, -14.0, 14.0, 28.0)])


def s13_checks(e, info):
    lab = info['labels']
    hide = info['A']['gk_hide']
    fk = e.fighter(3)
    flags = 0x0F000314
    for i in range(8):
        e.setw(hide + 4 * i, 0)
        e.setw(hide + 0x20 + 4 * i, 0)
    e.vars = {flags: 1.0}
    e.calls = []
    e.mu.reg_write(UC_PPC_REG_1, 0x700F0000)
    sp = 0x700F0000
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk['f'], 0x53)
    check('slot 13, bit 1: his slot\'s (3) hide counter = 4', [e.w(hide + 4 * i) for i in range(8)], [0, 0, 0, 4, 0, 0, 0, 0])
    if 'skeleton' in info['feats']:
        check('skeleton v1: slot 13 writes his VAR_14 = the clear-all count & 7 (his MSC resets on a change: a training '
              'reset)', e.vars.get(C.VAR_GEN_CLR), float(e.w(info['A']['gk_clr']) & 7))
    check('slot 13: on to his own code (stwu replayed, r3 / r4 / r5 kept, the non-volatiles kept)',
          (e.mu.reg_read(UC_PPC_REG_1), e.r(3), e.r(4), e.r(5), e.kept()), (0x700F0000 - 0x70, 0x51, fk['f'], 0x53, True))
    check('no slow without bit 2', [c for c in e.calls if c[0].startswith('slow')], [])
    e.vars = {flags: 2.0}
    e.calls = []
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk['f'], 0x53)
    check('bit 2: the Timer\'s slow on him (slot 3, rate 2, 600 frames, owner none)',
          [c for c in e.calls if c[0].startswith('slow')], [('slow_set', fk['slow'], 3, 2, 600, 0, 0x50000000)])
    check('the hide counter left alone without bit 1', e.w(hide + 12), 4)
    e.calls = []
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk['f'], 0x53)
    check('bit 2 still on: not again', [c for c in e.calls if c[0].startswith('slow')], [])
    e.vars = {flags: 0.0}
    e.calls = []
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk['f'], 0x53)
    check('bit 2 off: the slow cleared (vt +0x6C, slot 3)', [c for c in e.calls if c[0].startswith('slow')],
          [('slow_clr', fk['slow'], 3)])
    e.calls = []
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk['f'], 0x53)
    check('off and cleared: nothing more', [c for c in e.calls if c[0].startswith('slow')], [])
    stray = e.fighter(None)
    e.vars = {flags: 3.0}
    e.calls = []
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, stray['f'], 0x53)
    check('a fighter not in the table: nothing', ([c for c in e.calls if c[0] != 'getf'], [e.w(hide + 4 * i) for i in range(8)]),
          ([], [0, 0, 0, 4, 0, 0, 0, 0]))
    fk7 = e.fighter(7)
    e.vars = {flags: 7.0}
    e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk7['f'], 0x53)
    check('slot 7: its counter', e.w(hide + 28), 4)
    # v7: the tag message (the SET_CURSOR route) while bit 1 is on: at once, then every TAG_RESEND frames; visible 1 at the end
    tags = info['A']['gk_tags']
    for i in range(8):
        e.setw(tags + 4 * i, 0)
    e.setw(e.w(fk['f'] + C.BASE_ACC), 0x1234)               # his object id at [accessor + 0]

    def frame(f):
        e.vars = {flags: f}
        e.calls = []
        e.run_to(lab['s13'], C.SLOT13 + 4, 0x51, fk['f'], 0x53)
        return [c for c in e.calls if c[0] in ('msg_handle', 'msg_send')]
    # v9: the message's first word read from the game's own SET_CURSOR handler (0x02BE7C80: lis r11, 0x1010 at
    # +0x48, addi r11, r11, -0x3400 at +0x58 = 0x100FCC00, the message vtable); v7 / v8 had 0x1010CC00 (string data:
    # the user's tag never hid)
    hw, aw = e.w(0x02BE7CC8), e.w(0x02BE7CD8)
    game_kind = (((hw & 0xFFFF) << 16) + K.sx16(aw)) & 0xFFFFFFFF
    check('v9: the SET_CURSOR handler\'s message vtable (lis 0x%X / addi %d: 0x%08X) is ours'
          % (hw & 0xFFFF, K.sx16(aw), game_kind), (hw >> 26, aw >> 26, game_kind), (15, 14, C.MSG_KIND))
    want0 = [('msg_handle', 0x1234, 1), ('msg_send', C.MSG_KIND, 6, 0xA, 0)]
    check('v7: bit 1 on: the SET_CURSOR message {0xA, 0} to his object (handle (manager, id, 1), then sent)', frame(1.0), want0)
    n = [len(frame(1.0)) for _ in range(C.TAG_RESEND - 1)]
    check('v7: ... not again for %d frames' % (C.TAG_RESEND - 1), sum(n), 0)
    check('v7: ... then again', frame(1.0), want0)
    check('v7: bit 1 off: {0xA, 1} once (the tag back)', (frame(0.0), frame(0.0)),
          ([('msg_handle', 0x1234, 1), ('msg_send', C.MSG_KIND, 6, 0xA, 1)], []))


def s42_checks(e, info):
    lab = info['labels']
    fk = e.fighter(1, x=5.0)
    flags, hit = 0x0F000314, 0x0F000315
    rec = e.alloc(0x40, b'\0')
    e.setw(rec + 0x18, 0x10010022)
    msg = e.alloc(0x40, b'\0')
    e.setw(msg + 0x10, rec)
    for grp, fl, gone, x, want in ((1, 4.0, 0, 30.0, 10025.0), (1, 5.0, 0, -12.0, 9983.0), (1, 4.0, 1, 30.0, 10000.0)):
        e.setw(msg + 0x14, grp)
        e.vars = {flags: fl}
        e.gone, e.obj_x = gone, x
        e.calls = []
        r = e.call(lab['s42'], 0x61, fk['f'], msg)
        check('slot 42: group 1, clones out, the object at %g (him at 5, gone %d) -> VAR_21 %g, back to the caller'
              % (x, gone, want), (e.vars.get(hit), e.mu.reg_read(UC_PPC_REG_1)), (want, 0x700F0000))
        check('the object found by the record\'s id (+0x18)', [c[3] for c in e.calls if c[0] == 'handle'], [0x10010022])
    for grp, fl in ((0, 4.0), (1, 1.0), (1, 2.0)):
        e.setw(msg + 0x14, grp)
        e.vars = {flags: fl}
        e.calls = []
        e.run_to(lab['s42'], C.SLOT42 + 4, 0x61, fk['f'], msg)
        check('slot 42: group %d, flags %g -> his own code (stwu replayed, registers kept), VAR_21 untouched' % (grp, fl),
              (e.mu.reg_read(UC_PPC_REG_1), e.r(3), e.r(4), e.r(5), e.kept(), hit in e.vars),
              (0x700F0000 - 0xC8, 0x61, fk['f'], msg, True, False))


def s43_checks(e, info):
    lab = info['labels']
    fk = e.fighter(2)
    hit = 0x0F000315
    msg = e.alloc(0x40, b'\0')
    e.setw(msg + 8, 0x02000000)
    e.vars = {hit: 10014.0}
    r = e.call(lab['s43'], 0x71, fk['f'], msg)
    check('slot 43 with a clone hit: 0, the handled bit', (r, bytes(e.mu.mem_read(msg + 8, 1))[0]), (0, 3))
    e.setw(msg + 8, 0x02000000)
    e.vars = {hit: 0.0}
    e.run_to(lab['s43'], C.SLOT43 + 4, 0x71, fk['f'], msg)
    check('slot 43 without one: his own code, the message untouched',
          (e.mu.reg_read(UC_PPC_REG_1), e.r(3), e.r(4), e.r(5), e.kept(), e.w(msg + 8)),
          (0x700F0000 - 0x68, 0x71, fk['f'], msg, True, 0x02000000))


def plyc_checks(e, info, diag):
    """v10: the name tag at the player-cursor HUD's per-player call (PLYC_HOOK -> plyc -> PLYC_FN)"""
    lab, A = info['labels'], info['A']
    hide, saved = A['gk_hide'], A['gk_plyr']
    tw = [e.w(C.PLYC_TRAMP + 4 * i) for i in range(4)]
    check('v10: the per-player call of the cursor HUD update goes to plyc (through its trampoline)',
          (K.branch_target(C.PLYC_HOOK, e.w(C.PLYC_HOOK)), ((tw[0] & 0xFFFF) << 16) | (tw[1] & 0xFFFF), tw[2:]),
          (C.PLYC_TRAMP, lab['plyc'], [0x7D8903A6, 0x4E800420]))
    hud = e.alloc(8 * C.PLYC_BLK + 0x100, b'\0')
    for i in range(8):
        e.setw(hide + 4 * i, 0)
        e.setw(saved + 4 * i, 0)
        e.mu.mem_write(hud + i * C.PLYC_BLK + C.PLYC_SHOW, b'\x01')
        e.mu.mem_write(hud + i * C.PLYC_BLK + C.PLYC_ID, struct.pack('>h', i))
    e.stub(C.PLYC_FN, lambda e_: e_.calls.append(('plyc_fn', e_.r(3), e_.r(4),
                                                    e_.mu.mem_read(e_.r(3) + e_.r(4) * C.PLYC_BLK + C.PLYC_SHOW, 1)[0])))
    show = lambda i: e.mu.mem_read(hud + i * C.PLYC_BLK + C.PLYC_SHOW, 1)[0]

    def call(i):
        e.calls, e.osr_full = [], []
        e.call(lab['plyc'], hud, i)
        return [c for c in e.calls if c[0] == 'plyc_fn']
    check('v10: no hide counter: the game\'s per-player update as it is (show byte 1)', call(2), [('plyc_fn', hud, 2, 1)])
    e.setw(hide + 4 * 2, 2)
    got = call(2)
    logs = [x[:6] for x in e.osr_full]
    check('v10: his counter on: the show byte 0 before the game reads it, the counter counted down, the byte\'s value '
          'kept (+1)', (got, e.w(hide + 8), e.w(saved + 8)), ([('plyc_fn', hud, 2, 0)], 1, 2))
    if diag:
        check('v10 diag: S4GU once at the hide (hud, player 2, id 2, show 1)', logs,
              [(A['gk_fu'], hud, 2, 2, 1, 0)])
    e.mu.mem_write(hud + 2 * C.PLYC_BLK + C.PLYC_SHOW, b'\x01')   # the game set it again
    got = call(2)
    check('v10: ... the next frame: 0 again, no second log', (got, e.osr_full), ([('plyc_fn', hud, 2, 0)], []))
    got = call(2)
    check('v10: the counter run out: the saved byte (1) back once, then left alone',
          (got, e.w(saved + 8), call(2)), ([('plyc_fn', hud, 2, 1)], 0, [('plyc_fn', hud, 2, 1)]))
    e.setw(hide + 4 * 5, 3)
    call(5)
    check('v10: another player\'s counter: only that block', [show(i) for i in range(8)], [1, 1, 1, 1, 1, 0, 1, 1])
    e.setw(hide + 4 * 5, 0)
    call(5)
    check('v10: player 8+ (none): straight through', [c[:3] for c in call(9)], [('plyc_fn', hud, 9)])


def sway_checks(e, info):
    """v13: the clone's swing (feature sway): wp_94 -> w_sway: bind a swing system when its motion has none (its model
    instance's sb / nhb, or his), then the motion object's swing rate + step"""
    lab, A, F = info['labels'], info['A'], info['feats']
    if 'sway' not in F:
        check('v11: without "sway": no swing step code', 'w_sway' in lab, False)
        return
    calls = []
    newsw = [0]
    e.stub(C.SWING_RATE, lambda e_: calls.append(('rate', e_.r(3), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3))))
    e.stub(C.SWING_STEP, lambda e_: calls.append(('step', e_.r(3))))
    e.stub(C.SWING_UPDATE, lambda e_: calls.append(('whole update', e_.r(3))))
    e.stub(C.SWING_NEW, lambda e_: (calls.append(('new',)), newsw[0])[1])
    e.stub(C.SWING_SKEL, lambda e_: calls.append(('skel',) + tuple(e_.r(i) for i in range(3, 9))))
    e.stub(C.SWING_SB, lambda e_: calls.append(('sb', e_.r(3), e_.r(4))))
    e.stub(C.SWING_NHB, lambda e_: calls.append(('nhb', e_.r(3), e_.r(4))))
    cv = {C.VAR_SLOT: 3.0}
    vt = e.alloc(0x100, b'\0')
    g, st = e.alloc(4), e.alloc(4)
    e.setw(vt + 0x44, g)
    e.setw(vt + 0x4C, st)
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(cv.get(e_.r(4), 0.0))))
    e.stub(st, lambda e_: cv.__setitem__(e_.r(4), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)))
    wm = e.alloc(0x10, b'\0')
    e.setw(wm, vt)
    acc = e.alloc(0x100, b'\0')
    e.setw(acc + C.W_WORK, wm)
    mm = e.alloc(0x60, b'\0')
    e.setw(acc + C.W_MOTION, mm)
    motion = e.alloc(0x200, b'\0')
    e.setw(mm + C.MM_MODEL, motion)                     # v14: its model / motion object is MotionModule +0x10
    odd = e.alloc(0x40, b'\0')                         # +0x14 on a weapon: no such object (its +4 is 6: the user's
    e.setw(odd + 4, 6)                                   # v13 E_sway crash read 6's +4)
    e.setw(mm + C.MM_MOTION, odd)
    link = e.alloc(0x10, b'\0')
    e.setw(link + 4, 3)                                  # its model link's mode (8: none)
    e.setw(motion + 4, link)
    sk18 = e.alloc(0x10, b'\0')
    sk18a = e.alloc(0x10, b'\0')
    e.setw(sk18, sk18a)
    e.setw(sk18a + 8, 0x77)
    e.setw(motion + 0x18, sk18)
    e.setw(motion + 0x1C, 0x55500000)

    def model(acc_, sb, nhb):
        mmod = e.alloc(0x20, b'\0')
        mi = e.alloc(0x800, b'\0')
        e.setw(mmod + 0xC, mi)
        e.setw(mi + C.MI_SB, sb)
        e.setw(mi + C.MI_NHB, nhb)
        e.setw(acc_ + C.W_MODEL, mmod)
    model(acc, 0x11110000, 0x22220000)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, acc)

    def run():
        del calls[:]
        e.osr_full = []
        e.call(lab['w_sway'], weapon)
        return list(calls)
    sw = e.alloc(0x100, b'\0')
    newsw[0] = sw
    check('v13 sway: no swing system on its motion: one bound (new, the evaluator told, its sb / nhb parsed), then its '
          'rate (1.0) and step; never MotionModule\'s whole update',
          (run(), e.w(motion + C.MO_SWING)),
          ([('new',), ('skel', 0x55500000, sk18, sw, 9, 9, 0x77), ('sb', sw, 0x11110000), ('nhb', sw, 0x22220000),
            ('rate', motion, 1.0), ('step', motion)], sw))
    if info.get('diag'):
        check('v13 sway diag: S4GR 2 (sb, nhb, own 1), 3 (bound: motion, swing), 0 / 1 around its first step',
              [x[:5] for x in e.osr_full if x[0] == A['gk_fr']],
              [(A['gk_fr'], 2, 0x11110000, 0x22220000, 1), (A['gk_fr'], 3, motion, sw, 0),
               (A['gk_fr'], 0, motion, sw, 0), (A['gk_fr'], 1, motion, sw, 0)])
    check('v13 sway: the next frame: its rate and step only', run(), [('rate', motion, 1.0), ('step', motion)])
    # his sb when its own model has none; tried once a life
    e.setw(motion + C.MO_SWING, 0)
    cv[C.VAR_BIND] = 0.0
    model(acc, 0, 0)
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    me = e.fighter(2)
    e.mu.mem_write(me['f'] + 0x1E, b'\x04')
    model(e.w(me['f'] + C.BASE_ACC), 0x33330000, 0)
    newsw[0] = 0
    got = run()
    check('v13 sway: its own model without sb / nhb: his (slot 3) sb; the swing system not made: nothing more',
          got, [('new',)])
    check('v13 sway: ... not tried again this life (VAR_6)', run(), [])
    e.setw(link + 4, 8)
    cv[C.VAR_BIND] = 0.0
    check('v13 sway: its model link mode 8 (none): no bind', run(), [])
    e.setw(link + 4, 3)
    e.setw(acc + C.W_MOTION, 0)
    check('v12 sway: no MotionModule: nothing', run(), [])
    e.setw(acc + C.W_MOTION, mm)
    e.setw(mm + C.MM_MODEL, 0)
    cv[C.VAR_BIND] = 0.0
    check('v14 sway: the user\'s v13 crash layout (+0x10 none, +0x14 an object whose +4 is 6): nothing read through it, '
          'nothing called', (run(), e.w(odd + C.MO_SWING)), ([], 0))
    for bad, what in ((0x7, '+4 not a pointer'), (0x9000000, '+4 a low address')):
        e.setw(mm + C.MM_MODEL, motion)
        e.setw(motion + 4, bad)
        check('v14 sway: its object\'s %s: nothing' % what, run(), [])
    e.setw(motion + 4, link)
    sk1c = e.w(motion + 0x1C)
    e.setw(motion + 0x1C, 0x20)
    check('v14 sway: its evaluator (+0x1C) not a pointer: nothing', run(), [])
    e.setw(motion + 0x1C, sk1c)
    e.setw(motion + C.MO_SWING, sw)
    vtab = info['A']['w_vt']
    del calls[:]
    e.calls = []
    e.call(e.w(vtab + 0x94), 0x51, weapon, 0x55, 0x66)
    check('v12 sway: the +0x94 phase steps the swing, then runs the moon\'s method with its arguments as called',
          (calls, [c for c in e.calls if c[0].startswith('orig')]),
          ([('rate', motion, 1.0), ('step', motion)], [('orig94', 0x51, weapon, 0x55, 0x66)]))
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')


def hitcheck_checks(e, info, diag):
    """v12: the clone hit from his side (feature hitcheck): w_hitchk against fake fighters' attack nodes"""
    lab, A, F = info['labels'], info['A'], info['feats']
    if 'hitcheck' not in F:
        check('v12: without "hitcheck": no hit check code', 'w_hitchk' in lab, False)
        return
    # the clone: its WorkModule (VAR_0 slot 3, VAR_1 id 2, VAR_4 latch), its place (50, 10)
    cv = {C.VAR_SLOT: 3.0, C.VAR_ID: 2.0, C.VAR_LATCH: 0.0}
    vt = e.alloc(0x100, b'\0')
    g, st = e.alloc(4), e.alloc(4)
    e.setw(vt + 0x44, g)
    e.setw(vt + 0x4C, st)
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(cv.get(e_.r(4), 0.0))))

    def cset(e_):
        v = round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)
        cv[e_.r(4)] = v
        e_.calls.append(('clone_set', e_.r(4), v))
    e.stub(st, cset)
    wm = e.alloc(0x10, b'\0')
    e.setw(wm, vt)
    cacc = e.alloc(0x100, b'\0')
    e.setw(cacc + C.W_WORK, wm)
    post = e.alloc(0x40, b'\0')
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.0, 10.0))
    e.setw(cacc + C.W_POSTURE, post)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, cacc)

    def team(acc, tid):
        t = e.alloc(0x10, b'\0')
        e.setw(t + 8, tid & 0xFFFFFFFF)
        e.setw(acc + C.TEAM_MOD, t)

    def nodes_entry(ent, first, boxes):
        e.setw(ent, first)
        e.setw(ent + 4, len(boxes))
        out = []
        for i, (on, box) in enumerate(boxes):
            n = e.alloc(0x60, b'\0')
            e.mu.mem_write(n + C.NODE_ON, bytes([on]))
            e.mu.mem_write(n + C.NODE_MIN_X, struct.pack('>4f', *box))
            e.setw(ent + C.ENT_NODES + 4 * (first + i), n)
            out.append(n)
        return out

    stopvt = e.alloc(0x100, b'\0')
    stopfn = e.alloc(4)
    e.setw(stopvt + 0x8C, stopfn)
    e.stub(stopfn, lambda e_: e_.rec('hc_stop', 3, 4, 5))

    def attack_module(acc, tid, entries):
        team(acc, tid)
        am = e.alloc(0x60, b'\0')
        data = e.alloc(C.SLOT_SIZE * max(1, len(entries)), b'\0')
        for k in range(len(entries)):
            e.mu.mem_write(data + C.SLOT_SIZE * k + C.SLOT_DMG, struct.pack('>f', 9.0 + k))
        e.setw(am + C.AM_DATA, data)
        stop = e.alloc(0x10, b'\0')
        e.setw(stop, stopvt)
        e.setw(acc + C.W_STOP, stop)
        ents = e.alloc(C.ENT_SIZE * len(entries), b'\0')
        e.setw(am + C.AM_ENTS, ents)
        e.setw(am + C.AM_COUNT, len(entries))
        nodes = [nodes_entry(ents + C.ENT_SIZE * k, first, boxes) for k, (first, boxes) in enumerate(entries)]
        e.setw(acc + C.W_ATTACK, am)
        return nodes, data, stop

    def attacker(slot0, tid, entries):
        fk = e.fighter(slot0)
        e.mu.mem_write(fk['f'] + 0x1E, b'\x04')
        acc = e.w(fk['f'] + C.BASE_ACC)
        nodes, data, stop = attack_module(acc, tid, entries)
        fk.update(acc=acc, data=data, stop=stop)
        return fk, nodes
    if False:
        am = e.alloc(0x40, b'\0')
        ents = e.alloc(C.ENT_SIZE * len(entries), b'\0')
        e.setw(am + C.AM_ENTS, ents)
        e.setw(am + C.AM_COUNT, len(entries))
        nodes = [nodes_entry(ents + C.ENT_SIZE * k, first, boxes) for k, (first, boxes) in enumerate(entries)]
        e.setw(acc + C.W_ATTACK, am)
        return fk, nodes
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    me = e.fighter(2)                                     # his entry: slot 3
    e.mu.mem_write(me['f'] + 0x1E, b'\x04')
    team(e.w(me['f'] + C.BASE_ACC), 0)
    far = (200.0, 0.0, 210.0, 5.0)
    near = (54.0, 20.0, 60.0, 25.0)                       # its left edge inside x 44 - 56, y 10 - 28
    _a, an = attacker(4, 1, [(0, [(0, near)]), (2, [(1, far), (1, near)])])   # slot 5: entry 0 off, entry 1 node 2 on
    _t, tn = attacker(5, 0, [(0, [(1, near)])])          # slot 6: his team
    e.vars = {}

    def run():
        e.calls, e.osr_full = [], []
        e.call(lab['w_hitchk'], weapon)
        return ([c for c in e.calls if c[0] in ('setf', 'clone_set')],
                [x[:7] for x in e.osr_full if x[0] == A['gk_fh']])
    e.hs_ret = 7
    sets, logs = run()
    check('v13 hitcheck: the attacker\'s hitlag: HITSTOP_FN(its accessor, hitbox 1\'s data, its damage 10, mul, 1, 1) = 7 '
          'frames on its StopModule (vt +0x8C(7, 1))',
          ([c[:4] + c[5:] for c in e.calls if c[0] == 'hitstop'], [c for c in e.calls if c[0] == 'hc_stop']),
          ([('hitstop', _a['acc'], _a['data'] + C.SLOT_SIZE, 10.0, 1, 1)], [('hc_stop', _a['stop'], 7, 1)]))
    check('v12 hitcheck: slot 5\'s entry 1 (its second node on and over the clone\'s box): his VAR_21 = 20000 + its id '
          '2, the clone\'s latch 1; not his teammate (slot 6), not entry 0 (off)',
          sets, [('clone_set', C.VAR_LATCH, 1.0), ('setf', C.VAR_HIT, C.HIT_BIAS2 + 2)])
    if diag:
        check('v13 hitcheck diag: S4GH (attacker 0x05: fighter slot 5, hitbox 1, clone 2, hitlag 7, at 50, 10)', logs,
              [(A['gk_fh'], 5, 1, 2, 7, 50, 10)])
    check('v12 hitcheck: latched: no second report', run()[0], [])
    cv[C.VAR_LATCH] = 0.0
    e.mu.mem_write(an[1][1] + C.NODE_ON, b'\x00')
    check('v12 hitcheck: the node off: nothing', run()[0], [])
    e.mu.mem_write(an[1][1] + C.NODE_ON, b'\x01')
    for box, what in (((57.0, 12.0, 70.0, 20.0), 'right of it'), ((40.0, 29.0, 60.0, 40.0), 'above it'),
                      ((40.0, -5.0, 60.0, 9.0), 'below it')):
        e.mu.mem_write(an[1][1] + C.NODE_MIN_X, struct.pack('>4f', *box))
        check('v12 hitcheck: a node %s: nothing' % what, run()[0], [])
    e.mu.mem_write(an[1][1] + C.NODE_MIN_X, struct.pack('>4f', 30.0, 0.0, 45.0, 11.0))
    check('v12 hitcheck: a node touching its lower left corner: hit', run()[0],
          [('clone_set', C.VAR_LATCH, 1.0), ('setf', C.VAR_HIT, C.HIT_BIAS2 + 2)])
    cv[C.VAR_LATCH] = 0.0
    team(e.w(me['f'] + C.BASE_ACC), 1)
    e.mu.mem_write(tn[0][0] + C.NODE_ON, b'\x00')        # (slot 6, team 0, is an opponent now: its node off)
    check('v12 hitcheck: slot 5 on his team now: nothing (the same team skipped)', run()[0], [])
    e.mu.mem_write(tn[0][0] + C.NODE_ON, b'\x01')
    cv[C.VAR_LATCH] = 0.0
    sets, logs = run()
    check('v12 hitcheck: ... and slot 6 (team 0) an opponent now: its node hits',
          (sets, [x[1] for x in logs] if diag else [6]), ([('clone_set', C.VAR_LATCH, 1.0), ('setf', C.VAR_HIT, C.HIT_BIAS2 + 2)], [6]))
    cv[C.VAR_LATCH] = 0.0
    team(e.w(me['f'] + C.BASE_ACC), 0)
    cv[C.VAR_SLOT] = 5.0
    e.mu.mem_write(tn[0][0] + C.NODE_ON, b'\x00')
    check('v12 hitcheck: the clone owned by slot 5 (its node on it): its owner\'s own attack skipped', run()[0], [])
    cv[C.VAR_SLOT] = 3.0
    # v13: the weapons (holder +4) and items (+0x10): an object's +0x1E live, +0xC its accessor
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    e.mu.mem_write(me['f'] + 0x1E, b'\x04')
    cv[C.VAR_LATCH] = 0.0
    holder = e.w(C.FIGHTERS)

    def table(cat, size, objs):
        t = e.alloc(0x10, b'\0')
        arr = e.alloc(size * len(objs) + 0x40, b'\0')
        e.setw(t, arr)
        e.setw(t + 8, len(objs))
        e.setw(holder + 4 * cat, t)
        out = []
        for k, (live, tid, entries) in enumerate(objs):
            o = arr + size * k
            e.mu.mem_write(o + 0x1E, bytes([live]))
            acc = e.alloc(0x100, b'\0')
            e.setw(o + C.BASE_ACC, acc)
            out.append((acc, attack_module(acc, tid, entries)))
        return out
    wp = table(1, C.HC_OBJ_SIZES[1], [(4, 0, [(0, [(1, near)])]), (2, 1, [(0, [(1, near)])]), (4, 1, [(0, [(1, far)])])])
    check('v13 hitcheck: weapons: his team\'s (his shuriken, the clones), one not live, one away: nothing', run()[0], [])
    it = table(4, C.HC_OBJ_SIZES[4], [(4, 7, [(0, [(1, near)])])])
    sets, logs = run()
    check('v13 hitcheck: an item (another team) over it: hit; the item\'s hitlag', (sets, [c[1] for c in e.calls if c[0] == 'hitstop']),
          ([('clone_set', C.VAR_LATCH, 1.0), ('setf', C.VAR_HIT, C.HIT_BIAS2 + 2)], [it[0][0]]))
    if diag:
        check('v13 hitcheck diag: S4GH attacker 0x41 (category 4, its object 1)', [x[1] for x in logs], [0x41])
    cv[C.VAR_LATCH] = 0.0
    e.setw(holder + 0x10, 0)
    e.mu.mem_write(wp[2][1][0][0][0] + C.NODE_MIN_X, struct.pack('>4f', *near))
    sets, logs = run()
    check('v13 hitcheck: a weapon of another team over it: hit', sets,
          [('clone_set', C.VAR_LATCH, 1.0), ('setf', C.VAR_HIT, C.HIT_BIAS2 + 2)])
    if diag:
        check('v13 hitcheck diag: S4GH attacker 0x13 (category 1, its object 3)', [x[1] for x in logs], [0x13])
    e.setw(holder + 4, 0)
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')


def burn_checks(e, info, diag):
    """burn v1 (feature burn): his water moves' hits add burn instances to their victims; his ticks"""
    lab, A, F = info['labels'], info['A'], info['feats']
    fl = C.burn_floor(F)
    rows_all = C.burn_moves(F)
    check('burn: every move\'s instance, unshielded and shielded, totals at least %s %% (the user\'s floor%s): %s' % (
        fl, ', burn v2.1' if 'floor1' in F else '', ', '.join('%d %.2f / %.3f' % (m[0], C.burn_total(m), C.burn_total(m, True, fl))
                                                          for m in rows_all)),
          [(m[0], sh) for m in rows_all for sh in (False, True) if C.burn_total(m, sh, fl) < fl - 1e-4], [])
    check('burn: the shield clamp only where 50 %% / %d %% falls under the floor; above it the rule exact' % round(100 * C.BURN_SHIELD_DAMAGE),
          [m[0] for m in rows_all if (C.burn_shield_damage(m, fl) != m[1] * C.BURN_SHIELD_DAMAGE)
           != (m[1] * C.BURN_SHIELD_DAMAGE * (C.burn_shield_frames(m) // m[2]) < fl)], [])
    if 'floor1' in F:
        check('burn v2.1: shielded totals (35 %% a tick, half the frames, 1 %% floor): smashes 2.8 unclamped, forward air '
              '0.945 -> 1, neutral air 0.525 -> 1, skeleton 6.3, trail 0.525 -> 1',
              [(m[0], round(C.burn_total(m, True, fl), 4), m[1] * C.BURN_SHIELD_DAMAGE * (C.burn_shield_frames(m) // m[2]) < fl)
               for m in rows_all],
              [(95, 2.8, False), (99, 2.8, False), (101, 2.8, False), (105, 1.0, True), (104, 1.0, True),
               (C.SK_BURN_KEY, 6.3, False)] + ([(C.TR_BURN_KEY, 1.0, True)] if 'burn2' in F else []) +
              ([(C.SK_TOUCH_KEY, 1.0, True)] if 'sktouch' in F else []))
    if 'burn' not in F:
        check('burn: without "burn": no burn code', 'burn_him' in lab, False)
        return
    dm_calls = []
    dmvt = e.alloc(0x100, b'\0')
    dmadd = e.alloc(4)
    e.setw(dmvt + C.DM_ADD, dmadd)
    e.stub(dmadd, lambda e_: dm_calls.append((e_.r(3), e_.r(4), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 4))))
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')

    def fighter(slot0, kind=0):
        fk = e.fighter(slot0)
        e.mu.mem_write(fk['f'] + 0x1E, b'\x04')
        acc = e.w(fk['f'] + C.BASE_ACC)
        mm = e.alloc(0x60, b'\0')
        e.setw(mm + C.MM_KIND, kind)
        e.setw(acc + C.W_MOTION, mm)
        dm = e.alloc(0x10, b'\0')
        e.setw(dm, dmvt)
        e.setw(acc + C.W_DAMAGE, dm)
        fk.update(acc=acc, mm=mm, dm=dm)
        return fk

    def attack(acc, n_ents=2):
        am = e.alloc(0x60, b'\0')
        ents = e.alloc(C.ENT_SIZE * n_ents, b'\0')
        logs = []
        for k in range(n_ents):
            hdr = e.alloc(0x10, b'\0')
            e.setw(hdr + 4, hdr)
            e.setw(ents + C.ENT_SIZE * k + C.ENT_LOG, hdr)
            logs.append(hdr)
        e.setw(am + C.AM_ENTS, ents)
        e.setw(am + C.AM_COUNT, n_ents)
        e.setw(acc + C.W_ATTACK, am)
        return logs

    def log_hit(hdr, victim0, typ=1, cat=0):
        n = e.alloc(0x30, b'\0')
        e.setw(n + C.NODE_OBJ, (cat << 28) | (victim0 << 16) | 0x11)
        e.mu.mem_write(n + C.NODE_TYPE, bytes([typ]))
        last = hdr
        while e.w(last + 4) != hdr:
            last = e.w(last + 4)
        e.setw(n + 4, hdr)
        e.setw(last + 4, n)
        e.setw(hdr + 8, e.w(hdr + 8) + 1)
        return n

    def clear_log(hdr):
        e.setw(hdr + 4, hdr)
        e.setw(hdr + 8, 0)

    def inst(v):
        out = []
        for k in range(C.BURN_CAP):
            a = A['btab'] + (v * C.BURN_CAP + k) * 16
            fr, tk, ow = e.w(a), e.w(a + 4), e.w(a + 8)
            if fr:
                out.append((fr, tk >> 16, tk & 0xFFFF, ow, round(struct.unpack('>f', struct.pack('>I', e.w(a + 12)))[0], 4)))
        return out

    def frame(fk, slot0):
        e.calls, e.osr_full = [], []
        del dm_calls[:]
        e.call(lab['burn_him'], fk['f'], slot0)
        return list(dm_calls)
    gk = fighter(2, 95)                     # him: slot 3, forward smash
    vic = fighter(4)                         # the victim: slot 5
    logs = attack(gk['acc'])
    log_hit(logs[1], 4, 1)
    frame(gk, 2)
    check('burn: his forward smash hits slot 5: one instance (240 frames - 1 ticked, its tick 6 - 1, interval 6, owner '
          '3, 0.4 %)', inst(4), [(239, 5, 6, 2, 0.4)])
    if diag:
        check('burn diag: S4BA (victim 4, move 95, not shielded, 400, interval 6, 240 frames)',
              [x[:7] for x in e.osr_full if x[0] == A['gk_fba']], [(A['gk_fba'], 4, 95, 0, 400, 6, 240)])
    frame(gk, 2)
    check('burn: the same log node: no second instance', len(inst(4)), 1)
    log_hit(logs[1], 4, 2)                   # a shield hit
    frame(gk, 2)
    sd = round(C.burn_shield_damage(C.BURN_MOVES[0], C.burn_floor(F)), 4)
    check('burn: a shielded hit: half the frames (120), %d %%%% of the damage (raised to the %g %%%% total floor if under it: '
          '%s a tick), its own timer' % (round(100 * C.BURN_SHIELD_DAMAGE), C.burn_floor(F), sd), inst(4),
          [(237, 3, 6, 2, 0.4), (119, 5, 6, 2, sd)])
    got = []
    for _ in range(3):
        got.append(frame(gk, 2))
    check('burn: ticks: the first at its 6th frame (0.4 %), the shielded one 2 frames later, each its own',
          got, [[], [], [(vic['dm'], 0, 0.4)]])
    got = [frame(gk, 2) for _ in range(2)]
    check('burn: ... the second\'s tick 2 frames after the first\'s', got, [[], [(vic['dm'], 0, sd)]])
    # the other moves; outside them nothing
    e.setw(gk['mm'] + C.MM_KIND, 0)
    log_hit(logs[0], 4, 1)
    frame(gk, 2)
    check('burn: Wait1 (not a burning move): its hit adds nothing (the log followed)', len(inst(4)), 2)
    e.setw(gk['mm'] + C.MM_KIND, 104)
    frame(gk, 2)
    check('burn: then neutral air: that old hit still nothing', len(inst(4)), 2)
    log_hit(logs[0], 4, 1)
    frame(gk, 2)
    check('burn: neutral air\'s new hit: 0.25 % every 15 frames for 180', inst(4)[-1], (179, 14, 15, 2, 0.25))
    clear_log(logs[0])
    log_hit(logs[0], 4, 1)
    frame(gk, 2)
    check('burn: the log restarted (a multi-hit\'s next hit): a new instance, stacked (4)', len(inst(4)), 4)
    log_hit(logs[0], 4, 3)
    log_hit(logs[0], 5, 1, cat=1)
    log_hit(logs[0], 9, 1)
    frame(gk, 2)
    check('burn: a reflector record, a weapon, a slot past 8: nothing', len(inst(4)), 4)
    # the cap
    for _ in range(40):
        log_hit(logs[0], 4, 1)
    frame(gk, 2)
    check('burn: 40 more hits: capped at %d' % C.BURN_CAP, len(inst(4)), C.BURN_CAP)
    # another Greninja's instances: not his ticks
    gk2 = fighter(6, 101)
    logs2 = attack(gk2['acc'], 1)
    log_hit(logs2[0], 5, 1)
    vic2 = fighter(5)
    for k in range(C.BURN_CAP):
        e.setw(A['btab'] + (4 * C.BURN_CAP + k) * 16, 0)
    frame(gk2, 6)
    check('burn: another Greninja (slot 7) hits slot 6: his instance (owner 6)', inst(5), [(239, 5, 6, 6, 0.4)])
    for _ in range(10):
        frame(gk, 2)
    check('burn: ... slot 3\'s frames don\'t tick it', inst(5), [(239, 5, 6, 6, 0.4)])
    # the whole duration: 40 ticks of 0.4, then gone
    total = 0.0
    n = 0
    for _ in range(239):
        for c in frame(gk2, 6):
            total += c[2]
            n += 1
    check('burn: forward smash over its 240 frames: 40 ticks, 16 %%, then gone (%.2f)' % total,
          (n, round(total, 3), inst(5)), (40, 16.0, []))
    # a victim gone: its instances end
    log_hit(logs2[0], 5, 1)
    frame(gk2, 6)
    e.mu.mem_write(vic2['f'] + 0x1E, b'\x00')
    for _ in range(6):
        frame(gk2, 6)
    check('burn: its victim no longer live: its burns end', inst(5), [])
    # burn v1.1: a KO (Dead 0xB1 / Rebirth 0xB2) ends every burn on the victim, anyone's, at once; no tick after it
    e.mu.mem_write(vic2['f'] + 0x1E, b'\x04')
    sm = e.alloc(0x60, b'\0')
    e.setw(e.w(vic2['f'] + C.BASE_ACC) + C.F_STATUS, sm)
    for st, ko in ((0x0, False), (0xB0, False), (0xB1, True), (0xB2, True), (0xB3, False)):
        e.setw(sm + C.ST_KIND, 0)
        log_hit(logs2[0], 5, 1)
        frame(gk2, 6)
        e.setw(A['btab'] + (5 * C.BURN_CAP + 7) * 16, 50)        # another Greninja's instance too (owner 2)
        e.setw(A['btab'] + (5 * C.BURN_CAP + 7) * 16 + 4, (1 << 16) | 6)
        e.setw(A['btab'] + (5 * C.BURN_CAP + 7) * 16 + 8, 2)
        before = len(inst(5))
        e.setw(sm + C.ST_KIND, st)
        got, seen = [], []
        for _ in range(12):
            got.append(frame(gk2, 6))
            seen += [x for x in getattr(e, 'osr_full', []) if diag and x[0] == A['gk_fbk']]
        if ko:
            check('burn v1.1: victim KO\'d (status 0x%X) with %d burns: the list empty at once, no tick after' % (st, before),
                  (before >= 2, inst(5), got), (True, [], [[]] * 12))
            if diag:
                check('burn v1.1 diag: S4BK (victim 5, status 0x%X, seen by slot 6) once' % st,
                      [x[1:4] for x in seen], [(5, st, 6)])
        else:
            check('burn v1.1: status 0x%X (not a KO): its burns stay and tick' % st,
                  (len(inst(5)) > 0, sum(len(g) for g in got) > 0), (True, True))
        for k in range(C.BURN_CAP):
            e.setw(A['btab'] + (5 * C.BURN_CAP + k) * 16, 0)
    e.setw(sm + C.ST_KIND, 0)
    e.mu.mem_write(vic2['f'] + 0x1E, b'\x00')
    # a clone's hits count for its owner
    for k in range(C.BURN_CAP * 8):
        e.setw(A['btab'] + k * 16, 0)
    e.mu.mem_write(vic2['f'] + 0x1E, b'\x04')
    cv = {C.VAR_SLOT: 3.0, C.VAR_ID: 2.0}
    vt = e.alloc(0x100, b'\0')
    g = e.alloc(4)
    e.setw(vt + 0x44, g)
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(cv.get(e_.r(4), 0.0))))
    wm = e.alloc(0x10, b'\0')
    e.setw(wm, vt)
    cacc = e.alloc(0x100, b'\0')
    e.setw(cacc + C.W_WORK, wm)
    cmm = e.alloc(0x60, b'\0')
    e.setw(cmm + C.MM_KIND, 99)
    e.setw(cacc + C.W_MOTION, cmm)
    clog = attack(cacc, 1)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, cacc)
    log_hit(clog[0], 5, 1)
    e.call(lab['w_burn'], weapon)
    check('burn: a clone\'s up smash hits slot 6: an instance owned by its owner (slot 3)', inst(5), [(240, 6, 6, 2, 0.4)])
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')


def clear_checks(e, info, diag):
    """burn v1.2: the per-match state is emptied by the game's clear-all chain (match start / end, training reset,
    restart): gk_clear, reached from the chain's last `b`, ends with `b CLEAR_BACK` keeping r3 / r10"""
    lab, A, F = info['labels'], info['A'], info['feats']
    from kind_expand_test import REGS as RG
    ct = info['clear_at']
    w = e.w(ct)
    tgt = ct + ((w & 0x3FFFFFC) ^ 0x2000000) - 0x2000000
    check('burn v1.2: the clear-all chain\'s last b (0x%08X) goes to gk_clear' % ct, tgt, lab['gk_clear'])
    burn = 'burn' in F
    if burn:
        for k in range(0, C.SLOTS * C.BURN_CAP * 16, 16):
            e.setw(A['btab'] + k, 100)          # a "previous match": every list full
            e.setw(A['btab'] + k + 4, (3 << 16) | 6)
            e.setw(A['btab'] + k + 8, k // 16 % 8)
        e.mu.mem_write(A['bproc'], b'\x07' * (C.burn_contexts(F) * C.BURN_ENTS))
    if 'burn2' in F:
        e.mu.mem_write(A['bfx_lvl'], b'\x00\x00\x00\x03' * (C.SLOTS + C.SLOTS * C.TR_CTX))
    for i in range(16):
        e.setw(A['gk_hide'] + 4 * i, 3)
    for i in range(C.SLOTS):
        e.setw(A['gk_tags'] + 4 * i, 9)
        e.setw(A['gk_plyr'] + 4 * i, 2)
    n0 = e.w(A['gk_clr'])
    e.mu.reg_write(RG[10], 0x10)
    e.call(lab['gk_clear'], 0x12345678, until=C.CLEAR_BACK)
    check('burn v1.2: gk_clear back at CLEAR_BACK with r3 / r10 kept', (e.r(3), e.r(10)), (0x12345678, 0x10))
    if 'btint' in F:
        check('burn tint v1: gk_clear: every victim\'s tint state tier 0, fade -1 (off the next frame)',
              [(e.w(A['bti_st'] + 16 * i), e.w(A['bti_st'] + 16 * i + 4)) for i in range(C.SLOTS)], [(0, 0xFFFFFFFF)] * C.SLOTS)
        for i in range(C.SLOTS):
            e.setw(A['bti_st'] + 16 * i + 4, 0)
    if burn:
        check('burn v1.2: every burn of the last match gone, the processed counts 0',
              (any(e.w(A['btab'] + k) for k in range(0, C.SLOTS * C.BURN_CAP * 16, 4)),
               bytes(e.mu.mem_read(A['bproc'], C.burn_contexts(F) * C.BURN_ENTS)).strip(b'\0')), (False, b''))
    if 'burn2' in F:
        check('burn v2: the fires shown and the trails\' contexts 0',
              bytes(e.mu.mem_read(A['bfx_lvl'], 4 * (C.SLOTS + C.SLOTS * C.TR_CTX))).strip(b'\0'), b'')
    check('burn v1.2: the tag hide counters / slow states / tag countdowns 0, the cursor bytes kept for their restore',
          ([e.w(A['gk_hide'] + 4 * i) for i in range(16)], [e.w(A['gk_tags'] + 4 * i) for i in range(C.SLOTS)],
           [e.w(A['gk_plyr'] + 4 * i) for i in range(C.SLOTS)]), ([0] * 16, [0] * C.SLOTS, [2] * C.SLOTS))
    check('burn v1.2: the clear counted (diag S4BR)', e.w(A['gk_clr']), n0 + 1)
    if burn:
        # the next match: a Greninja and a victim live again, nothing ticks
        dm_calls = []
        dmvt = e.alloc(0x100, b'\0')
        dmadd = e.alloc(4)
        e.setw(dmvt + C.DM_ADD, dmadd)
        e.stub(dmadd, lambda e_: dm_calls.append(e_.r(3)))
        gk = e.fighter(1)
        e.mu.mem_write(gk['f'] + 0x1E, b'\x04')
        vic = e.fighter(3)
        e.mu.mem_write(vic['f'] + 0x1E, b'\x04')
        acc = e.w(vic['f'] + C.BASE_ACC)
        dm = e.alloc(0x10, b'\0')
        e.setw(dm, dmvt)
        e.setw(acc + C.W_DAMAGE, dm)
        gacc = e.w(gk['f'] + C.BASE_ACC)
        mm = e.alloc(0x60, b'\0')
        e.setw(gacc + C.W_MOTION, mm)
        for _ in range(12):
            e.call(lab['burn_him'], gk['f'], 1)
        check('burn v1.2: the next match: 12 frames of his, no burn ticks on anyone', dm_calls, [])
        for i in range(8):
            e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')


def skeleton_checks(e, info, diag):
    """skeleton v1 (feature skeleton): the Running Skeleton's kind, claim, collision (the hydrant's GroundModule route),
    HP hit check (damage once per attack, his own skipped), explosion burn (the strongest row)"""
    lab, A, F, img = info['labels'], info['A'], info['feats'], info['img']
    rows = {m[0]: m for m in C.BURN_MOVES}
    if 'skeleton' in F:
        sk_row = rows[C.SK_BURN_KEY]
        tot = {k: C.burn_total(m) for k, m in rows.items()}
        check('skeleton: its burn row is the strongest (%.1f %% unshielded, the next %.1f %%)' % (
            tot[C.SK_BURN_KEY], max(v for k, v in tot.items() if k != C.SK_BURN_KEY)),
              max(tot, key=tot.get), C.SK_BURN_KEY)
        check('skeleton: its burn 0.6 %% every 6 frames for 360 = 36 %%; shielded 50 %% / %d %% = 0.21 %% x 30 = 6.3 %% '
              '(over the 3 %% floor: no clamp)' % round(100 * C.BURN_SHIELD_DAMAGE),
              (round(C.burn_total(sk_row), 3), round(C.burn_shield_damage(sk_row, C.burn_floor(F)), 4),
               round(C.burn_total(sk_row, True, C.burn_floor(F)), 3)),
              (36.0, 0.21, 6.3))
    if 'skeleton' not in F:
        check('skeleton: without "skeleton": no skeleton code', 'sk_frame' in lab, False)
        return
    T = info['T']
    k = C.SK_KIND - W.OLD_N
    check('skeleton tables: name / folder "skeleton", owner "gekkouga"',
          [e.cstr(e.w(T[nm] + 4 * C.SK_KIND)) for nm in ('owner', 'name', 'folder')], ['gekkouga', 'skeleton', 'skeleton'])
    check('skeleton tables: base kind Mario\'s pump (its template: the AttackModule\'s update), its own singleton / row',
          (e.w(T['bt'] + 4 * k), e.w(T['st'] + 4 * k), e.w(T['rt'] + 4 * k) + W.MODULE_TABLE & 0xFFFFFFFF),
          (C.ATTACK_BASE, A['sk_single'], A['sk_row']))
    u16 = e.mu.mem_read(T['u16'] + 2 * C.SK_KIND, 2)
    bun = img.h(W.STATIC_TABLES[2][1] + 2 * C.CLONE_BASE)
    check('skeleton tables: u16 flags bunshin\'s without the Final Smash categories and the owner\'s colour (c00 only)',
          struct.unpack('>H', bytes(u16))[0], bun & ~(C.CATEGORY_BITS | 0x10))
    row = [e.w(A['sk_row'] + 4 * j) for j in range(28)]
    check('skeleton row: slot 5 (its GroundModule) the hydrant\'s constructor (grounds from an .lvd); Attack (2) and the MSC '
          'agent (8) there', (row[5], row[2] == e.w(W.MODULE_TABLE + 0x70 * C.ATTACK_BASE + 8), row[8] != 0),
          (C.SK_GM_CTOR, True, True))
    e.call(e.w(T['dt'] + 4 * k))
    d = e.r(3)
    mi = e.w(d + 8)
    bd = W.descriptor_of(img, C.CLONE_BASE)
    check('skeleton descriptor: a bunshin copy (+0x1C as bunshin\'s, as the clone\'s), 3 motions (the hydrant\'s hash)',
          (d, e.w(d + 0x1C), e.w(mi + 4), [e.w(e.w(mi) + 8 * i) for i in range(3)]),
          (A['sk_desc'], img.w(bd + 0x1C), 3, [C.SK_MOTION] * 3))
    vt = A['sk_vt']
    check('skeleton singleton: +0x34 sk_start, +0x94 sk_94, +0xAC sk_hit, the rest the moon\'s',
          (e.w(A['sk_single']), e.w(vt + 0x34), e.w(vt + 0x94), e.w(vt + W.HIT_METHOD)),
          (vt, lab['sk_start'], lab['sk_94'], lab['sk_hit']))
    lst = e.w(A['gk_desc'] + 8)
    check('his article list: %d entries, article 8 the skeleton (%s)' % ((11 if 'pbeetle' in F else 10 if 'burn2' in F else 9), 'clone articles v1: 3, '
          'his and his clones\' stacked' if 'cart' in F else 'one at a time'),
          (e.w(lst + 4), [e.w(e.w(lst) + 16 * 8 + 4 * j) for j in range(4)]),
          ((11 if 'pbeetle' in F else 10 if 'burn2' in F else 9), [C.SK_KIND, C.SK_LEVELS if 'cart' in F else 1, 0, 0]))
    # ---- the game's side, stubbed
    calls = []
    st = dict(file=1, ground=1)
    mgr = e.alloc(0x40, b'\0')
    e.setw(C.RES_MGR, mgr)
    e.setw(mgr + 0x30, 0xABC0)
    gm = e.alloc(0x200, b'\0')
    e.setw(gm, C.SK_GM_VT)
    ground = e.alloc(0x200, b'\0')                   # its handle: +0 the ground (+0x34 its vertex count), +0x160 id
    gobj = e.alloc(0x100, b'\0')
    e.setw(ground, gobj)
    e.setw(gobj + 0x34, len(C.sk_verts(F)))   # (tuning v1, skbot: 5)
    vnodes = [e.alloc(0x20, b"\0") for _ in range(len(C.sk_verts(F)))]   # skeleton v1.4: its vertex list (+0x3C: +4 next, +8 / +0xC x / y)
    e.setw(gobj + 0x3C, vnodes[0])
    for a_, b_ in zip(vnodes, vnodes[1:]):
        e.setw(a_ + 4, b_)

    def res_get(e_):
        calls.append(('res_get', e_.r(3), e_.r(5), e_.r(6), e_.r(7)))
        e_.setw(e_.r(4), 0x1111)

    def res_find(e_):
        calls.append(('res_find', e_.w(e_.r(3)), e_.cstr(e_.r(5)), e_.r(6)))
        e_.setw(e_.r(4), 0x2222 if st['file'] else 0)

    def gc_make(e_):
        calls.append(('make', e_.r(3), e_.r(4), e_.r(5), e_.r(6)))
        if st['ground']:
            e_.setw(e_.r(3) + 0xF0, ground)

    def vert(name):
        def f(e_):
            xy = bytes(e_.mu.mem_read(e_.r(5), 8))
            if e_.r(4) < len(vnodes):
                e_.mu.mem_write(vnodes[e_.r(4)] + 8, xy)        # the game's: the vertex placed / moved
            calls.append((name, e_.r(3), e_.r(4)) + tuple(round(x, 3) for x in struct.unpack('>2f', xy)))
        return f

    def gc_free(e_):
        calls.append(('col_free', e_.r(3)))
        e_.setw(e_.r(3) + 0xF0, 0)
    e.stub(C.RES_GET, res_get)
    e.stub(C.RES_FIND, res_find)
    e.stub(C.RES_ASSIGN, lambda e_: calls.append(('assign', e_.r(3), e_.w(e_.r(4)))))
    e.stub(C.RES_FREE, lambda e_: calls.append(('res_free', e_.r(4))))
    e.stub(C.GC_MAKE, gc_make)
    e.stub(C.GC_ON, lambda e_: calls.append(('on', e_.r(3), e_.r(4))))
    e.stub(C.GC_ENABLE, lambda e_: calls.append(('enable', e_.r(3))))
    e.stub(C.GC_SETV, vert('setv'))
    e.stub(C.GC_MOVEV, vert('movev'))
    e.stub(C.GC_COMMIT, lambda e_: calls.append(('commit', e_.r(3))))
    e.stub(C.GC_FREE, gc_free)
    e.stub(C.GC_FRAME, lambda e_: calls.append(('gmframe', e_.r(3))))
    gmf = [('gmframe', gm)] if 'gmupd' in F else []      # skeleton v1.3: its GroundModule's frame update, moved frames
    # the skeleton: its WorkModule (sv), place (50, 10), GroundModule, AttackModule (its explosion's logs), motion
    sv = {}
    svt = e.alloc(0x100, b'\0')
    g, s_ = e.alloc(4), e.alloc(4)
    e.setw(svt + 0x44, g)
    e.setw(svt + 0x4C, s_)
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(sv.get(e_.r(4), 0.0))))

    def sset(e_):
        sv[e_.r(4)] = round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)
    e.stub(s_, sset)
    swm = e.alloc(0x10, b'\0')
    e.setw(swm, svt)
    sacc = e.alloc(0x100, b'\0')
    e.setw(sacc + C.W_WORK, swm)
    post = e.alloc(0x80, b'\0')
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.0, 10.0))
    pvt = e.alloc(0x100, b'\0')
    psc = e.alloc(4)
    e.setw(pvt + C.PM_SCALE, psc)
    e.stub(psc, lambda e_: calls.append(('scale', e_.r(3), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3))))
    e.setw(post, pvt)
    e.setw(sacc + C.W_POSTURE, post)
    e.setw(sacc + 0x2C, gm)
    smm = e.alloc(0x60, b'\0')
    e.setw(sacc + C.W_MOTION, smm)
    sam = e.alloc(0x60, b'\0')
    sents = e.alloc(C.ENT_SIZE, b'\0')
    slog = e.alloc(0x10, b'\0')
    e.setw(slog + 4, slog)
    e.setw(sents + C.ENT_LOG, slog)
    e.setw(sam + C.AM_ENTS, sents)
    e.setw(sam + C.AM_COUNT, 1)
    e.setw(sacc + C.W_ATTACK, sam)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, sacc)
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    for kk in range(C.SLOTS * C.BURN_CAP):
        e.setw(A['btab'] + 16 * kk, 0)

    scales = []

    def frame():
        del calls[:]
        e.calls, e.osr_full = [], []
        e.call(lab['sk_frame'], weapon)
        scales[:] = [c for c in calls if c[0] == 'scale']
        return [c for c in calls if c[0] != 'scale']

    def logs(fmt):
        return [x[1:8] for x in e.osr_full if x[0] == A[fmt]] if diag else []
    # its start
    sv.update({0x0F000300 + v: 9.0 for v in range(13)})
    del calls[:]
    e.call(lab['sk_start'], 0, weapon, 0)
    check('skeleton start: a last life\'s grounds removed (its GroundModule: the hydrant\'s class), VARs 0-12 = 0',
          (calls, [sv[0x0F000300 + v] for v in range(13)]), ([('col_free', gm)], [0.0] * 13))
    # the claim: him (slot 3, Greninja) asked for one at (40, 12), facing left
    me = e.fighter(2)
    e.mu.mem_write(me['f'] + 0x1E, b'\x04')
    team = e.alloc(0x10, b'\0')
    e.setw(e.w(me['f'] + C.BASE_ACC) + C.TEAM_MOD, team)
    other = e.fighter(1)
    e.setw(other['f'] + 4, 0x1)                          # slot 2: Mario, its VAR_15 on (not a Greninja)
    e.mu.mem_write(other['f'] + 0x1E, b'\x04')
    e.vars = {C.GK_VAR_SKREQ: 1.0, C.GK_VAR_SKX: 40.0, C.GK_VAR_SKY: 12.0, C.GK_VAR_SKDIR: -1.0}
    c0 = frame()
    check('skeleton claim: its owner the Greninja that asked (slot 3; slot 2 is no Greninja): VAR_0 3, its start '
          '(40, 12), way -1; his VAR_15 cleared',
          ([sv[C.SK_VAR_SLOT], sv[C.SK_VAR_X], sv[C.SK_VAR_Y], sv[C.SK_VAR_DIR]], e.vars[C.GK_VAR_SKREQ]),
          ([3.0, 40.0, 12.0, -1.0], 0.0))
    check('skeleton claim: phase 0 (its MSC not started): no collision yet', [c for c in c0 if c[0] != 'res_free'], [])
    if diag:
        check('skeleton diag: S4SS (slot 3, 40, 12, -1)', [x[:4] for x in logs('gk_fss')], [(3, 40, 12, 0xFFFFFFFF)])
    e.vars = {}
    # running: the grounds made from skeleton.lvd and placed at it
    sv[C.SK_VAR_PHASE] = 1.0
    c1 = frame()
    W_, B_, H_ = C.SK_W, C.SK_B, C.SK_H
    want_v = [(gm, i, 50.0 + vx, 10.0 + vy) for i, (vx, vy) in enumerate(C.sk_verts(F))]
    check('skeleton collision: as the hydrant\'s set-up: its kind\'s bundle (manager +0x30, kind 0x1A2, 0, 0), '
          '"skeleton.lvd" in it, GroundModule +0xEC = the file, the grounds made (gm, 1, 0, 0), its 4 vertices placed at '
          'it (x +- 6, y + 2 / + 28), the lines recomputed, on (v1.2: (gm, 1), then the grounds turned on), both handles '
          'released',
          c1, [('res_get', 0xABC0, C.SK_KIND, 0, 0), ('res_find', 0x1111, 'skeleton.lvd', 1), ('assign', gm + 0xEC, 0x2222),
               ('make', gm, 1, 0, 0)] + [('setv',) + v for v in want_v] +
              [('commit', gm), ('on', gm, 1), ('enable', gm), ('res_free', 2), ('res_free', 2)])
    check('skeleton collision: VAR_6 = 1 (made)', sv[C.SK_VAR_COL], 1.0)
    check('skeleton: running, its stand-in body x %g (PostureModule vt +0xE4)' % C.SK_SCALE, scales, [('scale', post, C.SK_SCALE)])
    if diag:
        check('skeleton diag: S4SC state 1, its first ground, the bundle / lvd handles found, its GroundModule',
              [x[:5] for x in logs('gk_fsc')], [(1, ground, 0x1111, 0x2222, gm)])
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.7, 10.0))
    c2 = frame()
    check('skeleton collision: it moved 0.7: %sits vertices moved (riders carried: the move call), the lines recomputed, '
          'kept on (v1.2)' % ('v1.3: its GroundModule\'s frame update (GC_FRAME, as the hydrant\'s 0x02B38AD0) first, then '
                              if gmf else ''),
          c2, gmf + [('movev', gm, i, round(50.7 + vx, 3), 10.0 + vy) for i, (vx, vy) in enumerate(C.sk_verts(F))] +
          [('commit', gm), ('enable', gm)])
    if diag:
        want4 = [int(round(10 * v)) for vx, vy in C.sk_verts(F) for v in (50.7 + vx, 10.0 + vy)]
        got4 = [x[2:6] for x in logs('gk_fsd')][-1:] + [x[3:7] for x in logs('gk_fsv')][-1:]
        check('skeleton v1.4 diag: S4SD v0 / v1 and S4SV its place (507, 100) and v2 / v3 (x10): all 4 vertices as moved '
              '(the walls\' ends too)', ([list(g_) for g_ in got4], [x[1:3] for x in logs('gk_fsv')][-1:]),
              ([want4[:4], want4[4:8]], [(507, 100)]))
        if 'skbot' in F:
            check('tuning v1 diag (skbot): S4SB its bottom\'s end, vertex 4 (x10: its left wall\'s foot again), its ground',
                  [x[0:3] for x in logs('gk_fsb')][-1:], [(want4[8], want4[9], logs('gk_fsv')[-1][0])])
    e.setw(ground + 0x160, 0xFFFF0000)
    check('skeleton v1.1: its ground gone (id -1: something removed it): nothing moved; made again next frame (VAR_6 0, '
          'VAR_12 1)', (frame(), sv[C.SK_VAR_COL], sv[C.SK_VAR_REMADE]), ([], 0.0, 1.0))
    if diag:
        check('skeleton v1.1 diag: S4SG (owner 3, #1)', [x[:2] for x in logs('gk_fsg')], [(3, 1)])
    e.setw(ground + 0x160, 0)
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.0, 10.0))
    check('skeleton v1.1: ... made again at it', [c[0] for c in frame()][:4], ['res_get', 'res_find', 'assign', 'make'])
    for k in range(C.SK_REMAKE - 1):
        e.setw(ground + 0x160, 0xFFFF0000)
        frame()
        e.setw(ground + 0x160, 0)
        frame()
    e.setw(ground + 0x160, 0xFFFF0000)
    frame()
    check('skeleton v1.1: gone a %d%s time: lost for good (VAR_6 4: not made again)' % (C.SK_REMAKE + 1, 'th'),
          (sv[C.SK_VAR_COL], [c[0] for c in frame()]), (4.0, []))
    e.setw(ground + 0x160, 0)
    sv.update({C.SK_VAR_COL: 1.0, C.SK_VAR_REMADE: 0.0})
    e.setw(gobj + 0x34, 2)
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.0, 10.0))
    check('skeleton v1.1: a floor-only skeleton.lvd (2 vertices, as the hydrant\'s): only its top line moved (x +- 6, y + 28)',
          frame(), gmf + [('movev', gm, i, 50.0 + vx, 10.0 + vy) for i, (vx, vy) in enumerate(C.sk_verts(F)[1:3])] +
          [('commit', gm), ('enable', gm)])
    e.setw(gobj + 0x34, len(C.sk_verts(F)))   # (tuning v1, skbot: 5)
    frame()
    # ---- hits: attackers over its box (x 44 - 56, y 10 - 38)
    stopvt = e.alloc(0x100, b'\0')
    stopfn = e.alloc(4)
    e.setw(stopvt + 0x8C, stopfn)
    e.stub(stopfn, lambda e_: e_.rec('sk_stop', 3, 4, 5))

    def attacker(slot0, tid, boxes, dmg=(9.0, 10.0)):
        fk = e.fighter(slot0)
        e.mu.mem_write(fk['f'] + 0x1E, b'\x04')
        acc = e.w(fk['f'] + C.BASE_ACC)
        t = e.alloc(0x10, b'\0')
        e.setw(t + 8, tid & 0xFFFFFFFF)
        e.setw(acc + C.TEAM_MOD, t)
        am = e.alloc(0x60, b'\0')
        data = e.alloc(C.SLOT_SIZE * len(boxes), b'\0')
        ents = e.alloc(C.ENT_SIZE * len(boxes), b'\0')
        nodes = []
        for kk, (on, box) in enumerate(boxes):
            e.mu.mem_write(data + C.SLOT_SIZE * kk + C.SLOT_DMG, struct.pack('>f', dmg[kk]))
            en = ents + C.ENT_SIZE * kk
            e.setw(en, 0)
            e.setw(en + 4, 1)
            n = e.alloc(0x60, b'\0')
            e.mu.mem_write(n + C.NODE_ON, bytes([on]))
            e.mu.mem_write(n + C.NODE_MIN_X, struct.pack('>4f', *box))
            e.setw(en + C.ENT_NODES, n)
            nodes.append(n)
        e.setw(am + C.AM_DATA, data)
        e.setw(am + C.AM_ENTS, ents)
        e.setw(am + C.AM_COUNT, len(boxes))
        e.setw(acc + C.W_ATTACK, am)
        stop = e.alloc(0x10, b'\0')
        e.setw(stop, stopvt)
        e.setw(acc + C.W_STOP, stop)
        p = e.alloc(0x40, b'\0')
        e.mu.mem_write(p + 0x10, struct.pack('>2f', 60.0, 12.0))
        e.setw(acc + C.W_POSTURE, p)
        return dict(acc=acc, nodes=nodes, data=data, stop=stop, f=fk['f'])
    near = (52.0, 20.0, 58.0, 25.0)                       # (over both boxes: v1 - v1.4's x 44 - 56, v1.5's 46.5 - 53.5)
    far = (200.0, 0.0, 210.0, 5.0)
    e.mu.mem_write(other['f'] + 0x1E, b'\x00')
    e.setw(team + 8, 0)
    a = attacker(4, 1, [(1, near), (1, far)])            # slot 5, another team: entry 0 over it (9 %), entry 1 away
    e.hs_ret = 5
    frame()
    check('skeleton hit: slot 5\'s entry 0 over it: VAR_4 9 (its damage), VAR_9 1 hit, the place (its X 60 kept in the '
          'box: 50 + %g, its Y 12 + 8 = 20)' % C.sk_dims(F)[0], [sv.get(v) for v in (C.SK_VAR_DMG, C.SK_VAR_HITS, C.SK_VAR_HX,
                                                                                   C.SK_VAR_HY)],
          [9.0, 1.0, 50.0 + C.sk_dims(F)[0], 20.0])
    check('skeleton hit: the attacker\'s hitlag (HITSTOP_FN on that hitbox, 5 frames on its StopModule)',
          ([c[1:3] for c in e.calls if c[0] == 'hitstop'], [c for c in e.calls if c[0] == 'sk_stop']),
          ([(a['acc'], a['data'])], [('sk_stop', a['stop'], 5, 1)]))
    if diag:
        check('skeleton diag: S4SH (owner 3, attacker 0x05, hitbox 0, 90, HP left 160, at 50 + %g, 20)' % C.sk_dims(F)[0],
              logs('gk_fsh'), [(3, 5, 0, 90, 160, int(50 + C.sk_dims(F)[0]), 20)])
    for _ in range(3):
        frame()
    check('skeleton hit: the same attack (its hitbox still on) 3 more frames: no more damage', sv[C.SK_VAR_DMG], 9.0)
    e.mu.mem_write(a['nodes'][0] + C.NODE_ON, b'\x00')
    frame()
    e.mu.mem_write(a['nodes'][0] + C.NODE_ON, b'\x01')
    frame()
    check('skeleton hit: its hitbox off a frame, then a new one: hit again (18)', sv[C.SK_VAR_DMG], 18.0)
    e.mu.mem_write(a['nodes'][0] + C.NODE_ON, b'\x00')
    frame()
    e.mu.mem_write(a['nodes'][0] + C.NODE_ON, b'\x01')
    e.mu.mem_write(a['nodes'][1] + C.NODE_MIN_X, struct.pack('>4f', *near))
    frame()
    check('skeleton hit: two of its hitboxes over it at once (9 / 10): one hit, the lowest id\'s (27)',
          (sv[C.SK_VAR_DMG], sv[C.SK_VAR_HITS]), (27.0, 3.0))
    frame()
    check('skeleton hit: ... and neither again while they stay on', sv[C.SK_VAR_DMG], 27.0)
    for n in a['nodes']:
        e.mu.mem_write(n + C.NODE_ON, b'\x00')
    frame()
    # his own: his body, his team's weapons
    mine = attacker(6, 0, [(1, near)])
    frame()
    check('skeleton hit: a fighter of his team (team 0): nothing', sv[C.SK_VAR_DMG], 27.0)
    e.mu.mem_write(mine['f'] + 0x1E, b'\x00')
    macc = e.w(me['f'] + C.BASE_ACC)
    am = e.alloc(0x60, b'\0')
    ents = e.alloc(C.ENT_SIZE, b'\0')
    n = e.alloc(0x60, b'\0')
    e.mu.mem_write(n + C.NODE_ON, b'\x01')
    e.mu.mem_write(n + C.NODE_MIN_X, struct.pack('>4f', *near))
    e.setw(ents + 4, 1)
    e.setw(ents + C.ENT_NODES, n)
    e.setw(am + C.AM_ENTS, ents)
    e.setw(am + C.AM_COUNT, 1)
    e.setw(macc + C.W_ATTACK, am)
    e.setw(team + 8, 0xFFFFFFFF)
    frame()
    check('skeleton hit: its owner\'s own attack (him, FFA team -1): nothing', sv[C.SK_VAR_DMG], 27.0)
    e.setw(macc + C.W_ATTACK, 0)
    e.setw(team + 8, 0)
    # exploded: the grounds removed once, no more hits
    a2 = attacker(4, 1, [(1, near)])
    sv[C.SK_VAR_PHASE] = 2.0
    c3 = frame()
    check('skeleton exploded (phase 2): its grounds removed (anyone on it falls), VAR_6 2; no hit counted',
          ([c for c in c3 if c[0] == 'col_free'], sv[C.SK_VAR_COL], sv[C.SK_VAR_DMG]), ([('col_free', gm)], 2.0, 27.0))
    if diag:
        check('skeleton diag: S4SF (owner 3); S4SX phase 2 (damage 270)', (logs('gk_fsf')[:1] and [logs('gk_fsf')[0][:1]],
              [x[:3] for x in logs('gk_fsx')]), ([(3,)], [(3, 2, 270)]))
    check('skeleton exploded: not removed again; its scale 1 (the explosion\'s hitbox unscaled)',
          ([c for c in frame() if c[0] == 'col_free'], scales), ([], [('scale', post, 1.0)]))
    e.mu.mem_write(a2['f'] + 0x1E, b'\x00')
    # its explosion's hits: the skeleton row's burn for its owner (slot 3)
    vic = 5

    def log_hit(victim0, typ=1):
        nn = e.alloc(0x30, b'\0')
        e.setw(nn + C.NODE_OBJ, (victim0 << 16) | 0x11)
        e.mu.mem_write(nn + C.NODE_TYPE, bytes([typ]))
        last = slog
        while e.w(last + 4) != slog:
            last = e.w(last + 4)
        e.setw(nn + 4, slog)
        e.setw(last + 4, nn)
        e.setw(slog + 8, e.w(slog + 8) + 1)
    log_hit(vic, 1)
    log_hit(vic - 1, 2)
    frame()

    def inst(v):
        out = []
        for kk in range(C.BURN_CAP):
            at = A['btab'] + (v * C.BURN_CAP + kk) * 16
            if e.w(at):
                out.append((e.w(at), e.w(at + 4) & 0xFFFF, e.w(at + 8),
                            round(struct.unpack('>f', struct.pack('>I', e.w(at + 12)))[0], 4)))
        return out
    check('skeleton burn: its explosion hit slot 6: 0.6 %% every 6 frames for 360 (owner slot 3); shielded by slot 5: '
          '180 frames of 0.21 %%', (inst(vic), inst(vic - 1)), ([(360, 6, 2, 0.6)], [(180, 6, 2, 0.21)]))
    frame()
    check('skeleton burn: the same hits not again', (len(inst(vic)), len(inst(vic - 1))), (1, 1))
    for kk in range(C.SLOTS * C.BURN_CAP):
        e.setw(A['btab'] + 16 * kk, 0)
    if 'sktouch' in F:
        mark_checks(e, info, frame, log_hit, inst, sv, slog, vic, diag, logs, sacc, row)
    if 'cart' in F:
        cart_checks(e, info, frame, sv, sacc, post)
    # a missing .lvd: no collision, failed (3); the handles still released
    st['file'] = 0
    e.setw(gm + 0xF0, 0)
    sv.update({C.SK_VAR_PHASE: 1.0, C.SK_VAR_COL: 0.0})
    c4 = frame()
    check('skeleton collision: no skeleton.lvd: nothing made, VAR_6 3 (failed: not tried again), both handles released',
          ([c[0] for c in c4], sv[C.SK_VAR_COL]), (['res_get', 'res_find', 'res_free', 'res_free'], 3.0))
    check('skeleton collision: failed: not tried again', [c[0] for c in frame()], [])
    st['file'] = 1
    e.setw(gm, 0x10000000)
    sv[C.SK_VAR_COL] = 0.0
    c5 = frame()
    check('skeleton collision: its GroundModule not the hydrant\'s class: nothing called, failed (3)',
          ([c[0] for c in c5], sv[C.SK_VAR_COL]), ([], 3.0))
    e.setw(gm, C.SK_GM_VT)
    if diag:
        # v1.2: the hydrant's +0x94 (its lone blr) -> its trampoline -> hyd_diag: every 60 calls the S4C* lines, tag 2
        w = e.w(C.HYD_HOOK)
        check('skeleton v1.2 diag: the hydrant\'s +0x94 blr is a b to its trampoline', ((w >> 26) == 18,
              C.HYD_HOOK + (((w & 0x3FFFFFC) ^ 0x2000000) - 0x2000000)), (True, C.HYD_TRAMP))
        hgm = e.alloc(0x200, b'\0')
        hh = e.alloc(0x200, b'\0')
        hg = e.alloc(0x100, b'\0')
        ho = e.alloc(0x300, b'\0')
        e.setw(hgm + 0xF0, hh)
        e.setw(hh, hg)
        e.setw(hgm + 0x18, ho)
        for off, v in ((0x44, 0x01000000), (0x48, 0x02B34424), (0xA4, 0x01000000), (0xA8, 0x02B34470)):
            e.setw(hh + off, v)
        e.setw(hg + 0x34, 2)
        e.setw(hg + 0x68, 0x12345678)
        e.setw(ho + 0x248, 0x1000040E)
        hacc = e.alloc(0x100, b'\0')
        e.setw(hacc + 0x2C, hgm)
        hw = e.alloc(0x40, b'\0')
        e.setw(hw + C.W_ACC, hacc)
        e.setw(A['hyd_t'], 0)
        e.osr_full = []
        for _ in range(60):
            e.call(C.HYD_HOOK, 0x51, hw)
        got = {x[0]: x[1:8] for x in e.osr_full}
        check('skeleton v1.2 diag: 60 hydrant frames: S4CD (tag 2, its handle, +0x44 / +0x48 / +0xA4 / +0xA8), S4CE (+0x68), '
              'S4CG (its GroundModule, its +0x18 object\'s +0x248), S4CH (the ground\'s vertex count)',
              (len(e.osr_full), got.get(A['gk_fcd']), got.get(A['gk_fce'], (0,) * 5)[:5],
               got.get(A['gk_fcg'], (0,) * 7)[:3] + got.get(A['gk_fcg'], (0,) * 7)[6:7], got.get(A['gk_fch'], (0,) * 7)[6]),
              (5, (2, hh, 0, 0x01000000, 0x02B34424, 0x01000000, 0x02B34470), (2, hg, 0, 0, 0x12345678),
               (2, hgm, 0, 0x1000040E), 2))
        e.osr_full = []
        e.call(C.HYD_HOOK, 0x51, hw)
        check('skeleton v1.2 diag: ... not on the 61st', e.osr_full, [])
    # unowned: nothing
    sv.clear()
    check('skeleton: nobody asked for it: no owner, nothing', (frame(), sv.get(C.SK_VAR_SLOT, 0.0)), ([], 0.0))
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    e.hs_ret = 7


def mark_checks(e, info, frame, log_hit, inst, sv, slog, vic, diag, logs, sacc, row):
    """skeleton v1.7: the contact burn from every new hit record (feature mark: the append's trampoline clears a new
    record's +0x2E, burn_scan burns and marks every unmarked one; v1.5 / v1.6 counted records), its SoundModule (sksnd),
    its sound diag (S4SN)"""
    lab, A, F = info['labels'], info['A'], info['feats']
    sv[C.SK_VAR_PHASE] = 1.0                       # running: the contact row

    def clear():
        e.setw(slog + 4, slog)
        e.setw(slog + 8, 0)

    def standing(frames, how):
        for kk in range(C.SLOTS * C.BURN_CAP):
            e.setw(A['btab'] + 16 * kk, 0)
        clear()
        frame()
        for t in range(frames):
            if t % 3 == 0:
                if how == 'reset':
                    clear()                       # a new Hitbox command: the round's records freed ...
                log_hit(vic, 1)                   # ... and its next hit appended, the same frame (1 -> 0 -> 1)
            frame()
        return len(inst(vic))
    want = 20 if 'mark' in F else None
    got_reset = standing(60, 'reset')
    got_rehit = standing(60, 'rehit')
    if 'mark' in F:
        check('skeleton v1.7 (mark): a victim standing in the contact hitbox 60 frames, a hit every 3 frames: 20 contact '
              'burns, the hitbox set again before each hit in the same frame (the log 1 -> 0 -> 1: v1.6 counted 1) and '
              'a constant one with rehit 3 (the log growing)', (got_reset, got_rehit), (want, want))
        tot = sum(C.burn_total(C.SK_TOUCH_ROW) for _ in range(got_reset))
        check('skeleton v1.7: ... 20 x %.2f %% = %.0f %% a second (the user\'s ~70 %%)' % (C.burn_total(C.SK_TOUCH_ROW), tot),
              round(tot), 70)
        nodes = []
        n = e.w(slog + 4)
        while n != slog:
            nodes.append(e.mu.mem_read(n + C.MARK_OFF, 1)[0])
            n = e.w(n + 4)
        check('skeleton v1.7: every record scanned is marked (+0x2E = 0x%X)' % C.MARK, set(nodes), {C.MARK})
        # the trampoline: +0x2E cleared, then the game's append with r3 / r4 as they were, back to the caller
        seen = []
        e.stub(C.MARK_APPEND, lambda e_: seen.append((e_.r(3), e_.r(4), e_.mu.mem_read(e_.r(4) + C.MARK_OFF, 1)[0])))
        nd = e.alloc(0x30, b'\0')
        e.mu.mem_write(nd + C.MARK_OFF, bytes([C.MARK]))
        e.call(C.MARK_TRAMP, 0x1234, nd)
        check('skeleton v1.7: the mark trampoline (0x%08X): a reused record\'s +0x2E cleared, then the append (r3, r4 '
              'kept)' % C.MARK_TRAMP, seen, [(0x1234, nd, 0)])
        check('skeleton v1.7: the three record creators\' appends go through it (bl 0x%08X)' % C.MARK_TRAMP,
              [K.branch_target(a, e.w(a)) for a in C.MARK_SITES], [C.MARK_TRAMP] * 3)
    else:
        check('without "mark": the counts\' route (a re-set\'s hit in the frame of its clear is missed)', got_reset < 20, True)
    for kk in range(C.SLOTS * C.BURN_CAP):
        e.setw(A['btab'] + 16 * kk, 0)
    clear()
    if 'sksnd' in F:
        img = info['img']
        check('skeleton v1.7 (sksnd): row slot 11 (SoundModule, accessor +0xA4) the hydrant\'s / shuriken\'s constructor '
              '0x%08X; empty in bunshin\'s / the pump\'s rows (the setter 0x02BF682C then stores the null module 0x%08X, '
              'whose MSC handler is li r3, 0)' % (C.SND_CTOR, C.NULL_SOUND),
              (row[C.SND_SLOT], [bool(C.NULL_CTOR_OF(img, img.w(W.MODULE_TABLE + 0x70 * k + 4 * C.SND_SLOT)))
                                 for k in (C.CLONE_BASE, C.ATTACK_BASE, C.HYDRANT)],
               img.w(img.w(0x10100E64 + 0x18C) + 4)),
              (C.SND_CTOR, [True, True, False], 0x38600000))
        if diag:
            sv.update({C.SK_VAR_SNDN: 1.0, C.SK_VAR_SNDID: 91.0, C.SK_VAR_SNDR: 7.0})
            e.setw(sacc + 0xA4, 0xABCD00)
            frame()
            first = [x[:5] for x in logs('gk_fsn')]
            frame()
            again = [x[:5] for x in logs('gk_fsn')]
            sv.update({C.SK_VAR_SNDN: 2.0, C.SK_VAR_SNDID: 93.0, C.SK_VAR_SNDR: 0.0})
            frame()
            check('skeleton v1.7 diag: S4SN on each sound request (owner 3, #1, label 91, answer 7, its SoundModule), not '
                  'again, then #2 (93)', (first, again, [x[:5] for x in logs('gk_fsn')]),
                  ([(3, 1, 91, 7, 0xABCD00)], [], [(3, 2, 93, 0, 0xABCD00)]))
    sv[C.SK_VAR_PHASE] = 2.0


def cart_checks(e, info, frame, sv, sacc, post):
    """clone articles v1 (feature cart): the claim's level (his VAR_15 - 1), the stack table, the seat VARs, the latch banks"""
    A = info['A']
    got = []
    for req in (1.0, 2.0, 3.0):
        sv.update({C.SK_VAR_SLOT: 0.0, C.SK_VAR_LEVEL: 9.0, C.SK_VAR_PHASE: 0.0})
        e.vars = {C.GK_VAR_SKREQ: req, C.GK_VAR_SKX: 40.0, C.GK_VAR_SKY: 36.0, C.GK_VAR_SKDIR: 1.0}
        frame()
        got.append((sv[C.SK_VAR_SLOT], sv.get(C.SK_VAR_LEVEL), e.vars[C.GK_VAR_SKREQ]))
    e.vars = {}
    check('clone articles v1: the claim: his VAR_15 1 / 2 / 3 -> its level 0 (his) / 1 / 2 (his clones\', stacked), his '
          'request cleared', got, [(3.0, 0.0, 0.0), (3.0, 1.0, 0.0), (3.0, 2.0, 0.0)])
    seat = A['sk_seat']
    base = seat + ((3 - 1) * C.SK_LEVELS) * 16
    low = e.alloc(0x40, b'\0')
    e.setw(base, low)
    e.setw(base + 4, 17)
    e.mu.mem_write(base + 8, struct.pack('>2f', 30.0, 10.0))
    sv.update({C.SK_VAR_LEVEL: 1.0, C.SK_VAR_PHASE: 1.0})
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 30.0, 34.0))
    frame()
    me = base + 16
    check('clone articles v1: level 1 running: its entry (its accessor, its counter 1, x / y), the one below\'s read: VAR_17 '
          '1, VAR_18 / 19 its x / y (30, 10), VAR_21 its counter mod 10 (7)',
          ((e.w(me), e.w(me + 4), struct.unpack('>2f', bytes(e.mu.mem_read(me + 8, 8)))),
           [sv.get(k) for k in (C.SK_VAR_SEAT, C.SK_VAR_SEATX, C.SK_VAR_SEATY, C.SK_VAR_SEATN)]),
          ((sacc, 1, (30.0, 34.0)), [1.0, 30.0, 10.0, 7.0]))
    e.setw(base, 0)
    frame()
    check('clone articles v1: the one below gone (exploded / smoked: its entry let go): VAR_17 0 (it falls)',
          sv.get(C.SK_VAR_SEAT), 0.0)
    sv[C.SK_VAR_PHASE] = 2.0
    frame()
    check('clone articles v1: exploded: its own entry let go', e.w(me), 0)
    check('clone articles v1: a latch bank per level (3 x the attackers of every owner)',
          A['sk_seat'] - A['sk_latch'] >= C.SLOTS * C.SK_LATCH * 8 * C.SK_LEVELS, True)
    sv.update({C.SK_VAR_LEVEL: 0.0, C.SK_VAR_PHASE: 2.0})


def pose_checks(e, info, diag):
    """clones v14 (feature pose): his swing bones' world matrices onto the clone: C_b = C_a x inverse(H_a) x H_b"""
    import numpy as np
    lab, A, F = info['labels'], info['A'], info['feats']
    if 'pose' not in F:
        check('v14 pose: without "pose": no pose code', 'w_pose' in lab, False)
        return
    rng = np.random.default_rng(14)

    def rigid(scale):
        q = rng.normal(size=4)
        q /= np.linalg.norm(q)
        w, x, y, z = q
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M = np.zeros((3, 4))
        M[:, :3] = R * scale
        M[:, 3] = rng.normal(size=3) * 20
        return M

    def model(acc, mats, mode=0, count=C.POSE_MIN):
        mm = e.alloc(0x60, b'\0')
        obj = e.alloc(0x40, b'\0')
        e.setw(acc + C.W_MOTION, mm)
        e.setw(mm + C.MM_MODEL, obj)
        k = e.alloc(0x10, b'\0')
        e.setw(k + 4, mode)
        e.setw(obj + 4, k)
        ev = e.alloc(0x10, b'\0')
        e.setw(obj + 0x1C, ev)
        e.setw(obj + 0x30, count)                 # (the stub's answer)
        arr = e.alloc(0x30 * len(mats), b'\0')
        for i, m in enumerate(mats):
            e.mu.mem_write(arr + 0x30 * i, struct.pack('>12f', *m.reshape(-1)))
        e.setw(obj + C.MDL_MTX, arr)
        return arr

    e.stub(C.MDL_COUNT, lambda e_: e_.w(e_.r(3) + 0x30))

    def read(arr, i):
        return np.array(struct.unpack('>12f', bytes(e.mu.mem_read(arr + 0x30 * i, 0x30)))).reshape(3, 4)

    def h4(M):
        out = np.eye(4)
        out[:3, :] = M
        return out
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    him = e.fighter(2)
    e.mu.mem_write(him['f'] + 0x1E, b'\x04')
    H = [rigid(0.95).astype(np.float32).astype(float) for _ in range(C.POSE_MIN)]   # (as the game holds them)
    Cm = [rigid(0.95).astype(np.float32).astype(float) for _ in range(C.POSE_MIN)]
    harr = model(e.w(him['f'] + C.BASE_ACC), H)
    cv = {C.VAR_SLOT: 3.0, C.VAR_ID: 1.0}
    vt = e.alloc(0x100, b'\0')
    g, st = e.alloc(4), e.alloc(4)
    e.setw(vt + 0x44, g)
    e.setw(vt + 0x4C, st)
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(cv.get(e_.r(4), 0.0))))
    e.stub(st, lambda e_: cv.__setitem__(e_.r(4), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)))
    wm = e.alloc(0x10, b'\0')
    e.setw(wm, vt)
    cacc = e.alloc(0x100, b'\0')
    e.setw(cacc + C.W_WORK, wm)
    carr = model(cacc, Cm)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, cacc)
    e.osr_full = []
    e.call(lab['w_pose'], weapon, 8)
    want = {b: (h4(Cm[a]) @ np.linalg.inv(h4(H[a])) @ h4(H[b]))[:3] for b, a in C.POSE_BONES}
    err = max(float(np.abs(read(carr, b) - want[b]).max()) for b, _a in C.POSE_BONES)
    check('v14 pose: each of his 13 swing bones (tongue SWG_CMant0-8, the 4 water drops) on the clone = C_a x inverse(H_a) '
          'x H_b (a its nearest non-swing ancestor; uniform scale 0.95, random turns): max error %.2g' % err, err < 2e-3, True)
    others = [i for i in range(C.POSE_MIN) if i not in want]
    check('v14 pose: every other bone of the clone untouched',
          max(float(np.abs(read(carr, i) - Cm[i]).max()) for i in others), 0.0)
    # its tongue follows its head: the clone's tongue relative to its anchor is his
    b, a = C.POSE_BONES[4]
    rel_h = np.linalg.inv(h4(H[a])) @ h4(H[b])
    rel_c = np.linalg.inv(h4(Cm[a])) @ h4(read(carr, b))
    check('v14 pose: the clone\'s bone %d relative to its anchor %d is his (the tongue on its head)' % (b, a),
          float(np.abs(rel_h - rel_c).max()) < 2e-3, True)
    # nothing when: no owner, his model short of bones, mode 8, a zero scale anchor
    for what, setup, undo in (
            ('no owner (its VAR_0 0)', lambda: cv.__setitem__(C.VAR_SLOT, 0.0), lambda: cv.__setitem__(C.VAR_SLOT, 3.0)),
            ('his model with 60 bones', lambda: e.setw(e.w(e.w(e.w(him['f'] + C.BASE_ACC) + C.W_MOTION) + C.MM_MODEL) + 0x30, 60),
             lambda: e.setw(e.w(e.w(e.w(him['f'] + C.BASE_ACC) + C.W_MOTION) + C.MM_MODEL) + 0x30, C.POSE_MIN))):
        for i, m in enumerate(Cm):
            e.mu.mem_write(carr + 0x30 * i, struct.pack('>12f', *m.reshape(-1)))
        setup()
        e.call(lab['w_pose'], weapon, 8)
        check('v14 pose: %s: the clone untouched' % what,
              max(float(np.abs(read(carr, i) - Cm[i]).max()) for i in range(C.POSE_MIN)), 0.0)
        undo()
    # his MotionModule +0x14 (the object a fighter's swing update steps) is preferred when it is one; the clone's +0x14
    # (a weapon's: no such object, its +4 6) is never read through
    hacc = e.w(him['f'] + C.BASE_ACC)
    hmm = e.w(hacc + C.W_MOTION)
    H2 = [rigid(1.0).astype(np.float32).astype(float) for _ in range(C.POSE_MIN)]
    tmp = e.alloc(0x40, b'\0')
    e.setw(tmp + C.W_MOTION, e.alloc(0x60, b'\0'))
    arr2 = model(tmp, H2)
    e.setw(hmm + C.MM_MOTION, e.w(e.w(tmp + C.W_MOTION) + C.MM_MODEL))
    odd = e.alloc(0x40, b'\0')
    e.setw(odd + 4, 6)
    e.setw(e.w(cacc + C.W_MOTION) + C.MM_MOTION, odd)
    for i, m in enumerate(Cm):
        e.mu.mem_write(carr + 0x30 * i, struct.pack('>12f', *m.reshape(-1)))
    e.call(lab['w_pose'], weapon, 8)
    want2 = {b: (h4(Cm[a]) @ np.linalg.inv(h4(H2[a])) @ h4(H2[b]))[:3] for b, a in C.POSE_BONES}
    err = max(float(np.abs(read(carr, b) - want2[b]).max()) for b, _a in C.POSE_BONES)
    check('v14 pose: his +0x14 object (the swung one) used when it is one; the clone\'s odd +0x14 ignored (max error %.2g)'
          % err, err < 2e-3, True)
    e.setw(hmm + C.MM_MOTION, 0)
    if diag:
        cv[C.VAR_POSELOG] = 0.0
        for r in range(2):
            e.setw(A['pose_last'] + 0x14 * r + 0x10, 0)
        for i, m in enumerate(Cm):
            e.mu.mem_write(carr + 0x30 * i, struct.pack('>12f', *m.reshape(-1)))
        e.osr_full = []
        e.call(lab['w_pose'], weapon, 1)          # +0x64: the clone's pose (Cm, restored above) differs from our write
        e.call(lab['w_pose'], weapon, 8)          # +0x94: it is ours (no change): logs
        lg = [x for x in e.osr_full if x[0] == A['gk_ftp']]
        hb = H[C.POSE_LOG_BONE][:, 3] * 100
        cb = read(carr, C.POSE_LOG_BONE)[:, 3] * 100
        s32 = lambda v: v - (1 << 32) if v & 0x80000000 else v
        check('v14 pose diag: S4TP: bone 64\'s place on him / the clone (x100), the phases that found the clone\'s own pose '
              '(1: +0x64 after the restore; not +0x94)',
              (len(lg), [s32(v) for v in lg[0][1:7]] if lg else None, lg[0][7] if lg else None),
              (1, [int(v) for v in hb] + [int(v) for v in cb], 1))


def hud_checks(e, info):
    lab, A = info['labels'], info['A']
    hide = A['gk_hide']
    cur = e.alloc(0x40, b'\0')
    for player, cnt in ((3, 4), (3, 1), (0, 2), (7, 4)):
        for i in range(8):
            e.setw(hide + 4 * i, 0)
        e.setw(hide + 4 * player, cnt)
        e.mu.mem_write(cur + 8, struct.pack('>ff', 11.0, 22.0))
        e.mu.reg_write(REGS[29], 8 - player)
        e.calls = []
        e.call(lab['hud'], cur)
        check('HUD, player %d counter %d: the cursor far off, the counter %d, then the game\'s update (r3 the cursor)'
              % (player, cnt, cnt - 1),
              (struct.unpack('>ff', bytes(e.mu.mem_read(cur + 8, 8))), e.w(hide + 4 * player),
               [c for c in e.calls if c[0] == 'hudfn']), ((C.FAR, C.FAR), cnt - 1, [('hudfn', cur)]))
    for i in range(8):
        e.setw(hide + 4 * i, 0)
    e.mu.mem_write(cur + 8, struct.pack('>ff', 11.0, 22.0))
    e.mu.reg_write(REGS[29], 5)
    e.calls = []
    e.call(lab['hud'], cur)
    check('HUD, a stopped counter: the cursor untouched, the game\'s update',
          (struct.unpack('>ff', bytes(e.mu.mem_read(cur + 8, 8))), [c for c in e.calls if c[0] == 'hudfn']),
          ((11.0, 22.0), [('hudfn', cur)]))
    img = K.Image(sys.argv[2])
    check('the HUD hook: bl to the trampoline', K.branch_target(C.HUD_HOOK, img.w(C.HUD_HOOK)), C.TRAMP)


def panel_checks(e, info, diag):
    """v6: the damage panel gauge: the update hook (after the trait badge's / the game's update), per Greninja slot his
    VAR_19 on Little Mac's KO meter"""
    lab, A = info['labels'], info['A']
    P = e.alloc(0xC0 + 8 * C.PANEL_SLOT + 0x100, b'\0')
    slot = lambda i: P + 0xC0 + i * C.PANEL_SLOT
    for i in range(8):
        e.mu.mem_write(slot(i) + 8, struct.pack('>h', 2))          # empty
    fm = e.alloc(0x80, b'\0')
    e.setw(fm + 0x18, 4)
    e.setw(C.FIGHTER_MANAGER, fm)
    gk = e.fighter(None)                                          # his accessor's WorkModule (the variables)
    gacc = e.alloc(0x40, b'\0')
    gwm = gk['wm']
    e.setw(gacc + 0x28, gwm)

    def fighter_obj(entry, kind, acc):
        fe = e.alloc(0x2000, b'\0')
        e.setw(fm + 0x24 + 4 * entry, fe)
        e.mu.mem_write(fe + 0x14E9, b'\x00')
        e.setw(fe + 0xDB4, 1)
        obj = e.alloc(0x20, b'\0')
        e.setw(fe + 0xDC0, obj)
        e.setw(obj + 4, kind)
        e.setw(obj + 0xC, acc)
    fighter_obj(0, C.GK_KIND, gacc)
    macc = e.alloc(0x40, b'\0')
    fighter_obj(1, 0x29, macc)
    ko = e.alloc(0x20, b'\0')
    ko2 = e.alloc(0x20, b'\0')
    for i, entry, kind, k in ((0, 0, C.GK_KIND, ko), (2, 1, 0x29, ko2)):
        e.mu.mem_write(slot(i), struct.pack('>h', entry))
        e.mu.mem_write(slot(i) + 8, struct.pack('>h', 0))
        e.mu.mem_write(slot(i) + 0xA, bytes([kind]))
        e.setw(slot(i) + 0x18C, k)
    e.stub(C.PANEL_PREV, lambda e_: (e_.rec('prev', 3), 0x77)[1])
    e.stub(C.PANEL_VISIBLE, lambda e_: e_.rec('visible', 3, 4))
    e.stub(C.PANEL_KO_SET, lambda e_: e_.rec('ko_set', 3, 4, 5))
    e.stub(C.PANEL_COLOUR, lambda e_: e_.rec('colour', 3, 4))

    def run(g):
        e.vars = {C.VAR_GAUGE: float(g)}
        e.calls = []
        for i in range(14, 32):
            e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        r = e.call(lab['gk_panel'], P)
        return r, [c for c in e.calls if c[0] in ('prev', 'visible', 'ko_set', 'colour')], e.kept()
    check('v6 panel hook: the vtable +0x3C word is ours (it was the trait badge cave)', e.w(C.PANEL_VT), lab['gk_panel'])
    check('v6 panel: charge 1033 -> the previous update (its r3 kept), his slot\'s KO meter shown, 33, mode 1\'s colour; '
          'Little Mac\'s slot and the empty ones untouched; the registers kept', run(1033),
          (0x77, [('prev', P), ('visible', ko, 1), ('ko_set', P, 0, 33), ('colour', ko, A['ctf'] + 12)], True))
    check('v6 panel: ready 1100 -> 100 (the meter\'s blinking frame)', run(1100)[1][2], ('ko_set', P, 0, 100))
    check('v6 panel: the ability 2050 -> 50, blue (mode 2)', run(2050)[1][2:], [('ko_set', P, 0, 50), ('colour', ko, A['ctf'] + 24)])
    check('v6 panel: the burnout 3020 -> 20, grey (mode 3)', run(3020)[1][2:], [('ko_set', P, 0, 20), ('colour', ko, A['ctf'] + 36)])
    check('v6 panel: nothing (0) -> the meter hidden', run(0)[1], [('prev', P), ('visible', ko, 0)])
    check('v6 panel: a bad mode (7000) -> hidden', run(7000)[1][1:], [('visible', ko, 0)])
    g2 = 'gauge2' in info['feats']
    check('v6 gauge colours: as is / blue / grey%s' % (' (round gauge v1.1, gauge2: the charge cyan)' if g2 else ''),
          bytes(e.mu.mem_read(A['ctf'], 48)),
          b''.join(struct.pack('>4B4h', *c) for c in (C.GAUGE_COLOURS2 if g2 else C.GAUGE_COLOURS)))
    # v7: the round gauge (gkgauge_mc in his panel's root clip: tools/gekkouga_gauge_flx.py)
    root = e.alloc(0x100, b'\0')
    e.setw(slot(0) + 0x5C, root)
    clips = {n: e.alloc(0x100, b'\0') for n in C.GAUGE_NAMES}
    atoms = {n: 0x7000 + i for i, n in enumerate(C.GAUGE_NAMES)}
    pool = e.alloc(0x40, b'\0')
    e.setw(C.FLX_ATOM_POOL, pool)

    def intern(e_):
        name = bytes(e_.mu.mem_read(e_.r(4), e_.r(5))).decode()
        e_.calls.append(('intern', name, e_.r(3) == pool + 0x24))
        return atoms.get(name, 0)

    def find(e_):
        atom = e_.w(e_.r(4))
        parent = e_.r(3)
        known = [n for n, a_ in atoms.items() if a_ == atom]
        if not known:
            return None                 # (UI v1's clips: ui_checks' own stub answers)
        name = known[0]
        ok = (parent == root) if name == 'gkgauge_mc' else (parent == clips['gkgauge_mc'])
        return clips[name] if ok else 0
    e.stub(C.FLX_INTERN, intern)
    e.stub(C.FLX_FIND, find)
    e.stub(C.FLX_ROTATE, lambda e_: e_.calls.append(('rotate', e_.r(3), round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 2))))
    e.stub(C.FLX_GOTO, lambda e_: e_.calls.append(('goto', e_.r(3), e_.r(4))))
    for i in range(32):
        e.setw(A['gk_angles'] + 4 * i, 0)

    def run2(g):
        e.vars = {C.VAR_GAUGE: float(g)}
        e.calls = []
        e.call(lab['gk_panel'], P)
        return [c for c in e.calls if c[0] in ('visible', 'ko_set', 'colour', 'rotate', 'goto')]
    rings = [clips[n] for n in C.GAUGE_NAMES[1:5]]
    r = run2(1035)
    check('v7 round gauge: found in his panel -> the KO meter hidden, the gauge shown, mode 1\'s colour, each ring turned '
          'by its speed (first frame), the fill on frame 1 + 35 / 10 (rounded: 5)',
          r, [('visible', ko, 0), ('visible', clips['gkgauge_mc'], 1), ('colour', clips['gkgauge_mc'], A['ctf'] + 12)] +
          [('rotate', c, round(sp % 360.0, 2)) for c, sp in zip(rings, C.GAUGE_SPEEDS)] +
          [('goto', clips['gk_fill_mc'], 5)])
    check('v7: ... the fill stopped there (+0x9C = 1)', struct.unpack('>H', bytes(e.mu.mem_read(clips['gk_fill_mc'] + 0x9C, 2)))[0], 1)
    r = run2(1100)
    if 'gready' not in info['feats']:
        check('v7: the next frame the rings turn on (2 x speed, kept in 0-360), the full charge on frame 11',
              [c[2] for c in r if c[0] in ('rotate', 'goto')],
              [round((2 * sp) % 360.0, 2) for sp in C.GAUGE_SPEEDS] + [11])
    else:
        check('tuning v1 (gready): the charge full (1100): READY: the rings turn %d times a frame (2, 3, 4 x speed), the '
              'fill on frame 11, the pulse\'s first colour (gold)' % C.READY_SPIN,
              ([c[2] for c in r if c[0] in ('rotate', 'goto')], [c for c in r if c[0] == 'colour']),
              (sum(([round((n * sp) % 360.0, 2) for sp in C.GAUGE_SPEEDS] + [11] for n in (2, 3, 4)), []),
               [('colour', clips['gkgauge_mc'], A['ctf_ready'] + 0)]))
        cols = [[c[2] for c in run2(1100) if c[0] == 'colour'][0] for _ in range(70)]
        steps = [(x - A['ctf_ready']) // 12 for x in cols]
        check('... the pulse: a step every %d frames up 0 - 7 and down 7 - 0 (a cycle of 64 frames, about a second)' %
              C.READY_STEP, (steps, max(steps), steps.count(7)),
              ([min(q, 15 - q) for q in (((i + 2) // C.READY_STEP) % 16 for i in range(70))], 7, 2 * C.READY_STEP))
        check('... the ready colours: gold, alpha 70 -> 98 %, lit up to white-hot', bytes(e.mu.mem_read(A['ctf_ready'], 96)),
              b''.join(struct.pack('>4B4h', *c) for c in C.READY_COLOURS))
        r = run2(1099)
        check('... not full (1099): mode 1\'s cyan, the rings once, the pulse back to its start',
              ([c for c in r if c[0] == 'colour'], len([c for c in r if c[0] == 'rotate']), e.w(A['gk_pulse'])),
              ([('colour', clips['gkgauge_mc'], A['ctf'] + 12)], 4, 0))
    check('v7: the ability (2050): blue', [c for c in run2(2050) if c[0] == 'colour'], [('colour', clips['gkgauge_mc'], A['ctf'] + 24)])
    check('v7: nothing (0): the gauge hidden, no ring calls', run2(0), [('visible', ko, 0), ('visible', clips['gkgauge_mc'], 0)])
    check('v7: the names interned each frame from the atom pool', [c for c in e.calls if c[0] == 'intern' and c[1] == 'gkgauge_mc'][:1], [('intern', 'gkgauge_mc', True)])
    if 'gkui' in info['feats']:
        ui_checks(e, info, diag, P, slot, root, clips, ko, ko2)
    e.setw(slot(0) + 0x5C, 0)
    if diag:
        e.calls = []
        run(1033)
        n1 = len([c for c in e.calls if c[0] == 'osr'])
        run(1034)
        n2 = len([c for c in e.calls if c[0] == 'osr'])
        run(1043)
        n3 = len([c for c in e.calls if c[0] == 'osr'])
        check('v6 diag: S4GB logged when the gauge changes by a tenth (1034 no, 1043 yes)', (n2, n3), (0, 1))


def ui_checks(e, info, diag, P, slot, root, clips, ko, ko2):
    """UI radar / waveform v1 (feature gkui): gk_ui from gk_panel on his panel only: the radar (shown, the beetle shown /
    hidden by the Parabeetle's cooldown, the sweep's spin per state) and the waveform (shown, its frame by the smash
    charge, rainbow and fast at full, its colour) from his New_Var 58 (UI_VAR)"""
    lab, A = info['labels'], info['A']
    names = C.gauge_names(info['feats'])
    check('UI v1: the clip names after the round gauge\'s (gk_find indices 6 - 10: the panel\'s gekkouga_gauge_flx.UI_NAMES)',
          (names[len(C.GAUGE_NAMES):], [e.w(A['gk_names'] + 8 * i + 4) for i in range(len(names))]),
          (C.UI_NAMES, [len(n) for n in names]))
    check('UI v1: the constants: the sweep 3.6 / 0.9 degrees a frame (a turn in 100 / 400 frames: 1.67 s, a quarter speed '
          'on cooldown), 360; the colours (the radar as drawn, the waveform cyan below full, as drawn at full)',
          (struct.unpack('>3f', bytes(e.mu.mem_read(A['ui_k'], 12))), bytes(e.mu.mem_read(A['ui_col'], 36))),
          ((C.UI_SPEED, C.UI_SPEED_CD, 360.0), b''.join(struct.pack('>4B4h', *c) for c in C.UI_COLOURS)), tol=1e-5)
    check('UI v1: ... ready a turn per %.2f s, on cooldown per %.2f s (the user: "spin slowly")' % (
          360 / C.UI_SPEED / 60, 360 / C.UI_SPEED_CD / 60), (round(360 / C.UI_SPEED), round(C.UI_SPEED / C.UI_SPEED_CD, 3)),
          (100, 4.0))
    roots = {'his': root, 'mac': e.alloc(0x100, b'\0')}
    uclips = {(w, n): e.alloc(0x100, b'\0') for w in roots for n in C.UI_NAMES}
    atoms = {n: 0x7000 + i for i, n in enumerate(names)}
    for i in range(C.SLOTS):
        e.setw(A['ui_ang'] + 4 * i, 0)
    e.setw(slot(2) + 0x5C, roots['mac'])
    have = {'wave': True, 'beetle': True}

    def intern(e_):
        name = bytes(e_.mu.mem_read(e_.r(4), e_.r(5))).decode()
        return atoms.get(name, 0)

    def find(e_):
        atom, parent = e_.w(e_.r(4)), e_.r(3)
        name = [n for n, a_ in atoms.items() if a_ == atom][0]
        if name == 'gkgauge_mc':
            return clips[name] if parent == root else 0
        if name in C.GAUGE_NAMES:
            return clips[name] if parent == clips['gkgauge_mc'] else 0
        if name == 'gkwave_mc' and not have['wave'] or name == 'gk_rbeetle_mc' and not have['beetle']:
            return 0
        for w, r_ in roots.items():
            if name in ('gkradar_mc', 'gkwave_mc') and parent == r_:
                return uclips[(w, name)]
            if parent == uclips[(w, 'gkradar_mc')]:
                return uclips[(w, name)]
        return 0
    e.stub(C.FLX_INTERN, intern)
    e.stub(C.FLX_FIND, find)
    ui = {v: k[1] for k, v in uclips.items() if k[0] == 'his'}
    mac = set(v for k, v in uclips.items() if k[0] == 'mac')

    def frame(word, gauge=0):
        e.vars = {C.VAR_GAUGE: float(gauge), C.UI_VAR: float(word)}
        e.calls = []
        e.osr_full = []
        for i in range(14, 32):
            e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        e.call(lab['gk_panel'], P)
        out = []
        for c in e.calls:
            if c[0] in ('visible', 'colour', 'rotate', 'goto') and (c[1] in ui or c[1] in mac):
                out.append((c[0], ui.get(c[1], 'MAC:%X' % c[1])) + tuple(c[2:]))
        return out, e.kept()
    e.setw(A['ui_t'], 0)
    got, kept = frame(0)
    check('UI v1: ready, no charge (0): the radar shown in the radar colour, the beetle shown, the sweep turned 3.6 from 0; '
          'the waveform shown on frame %d (level 0, phase 0) in the calm cyan, stopped; the registers kept; Little Mac\'s '
          'panel (the same clips in it) untouched' % C.ui_frame(0, 1),
          (got, kept, struct.unpack('>H', bytes(e.mu.mem_read(uclips[('his', 'gkwave_mc')] + 0x9C, 2)))[0]),
          ([('visible', 'gkradar_mc', 1), ('colour', 'gkradar_mc', A['ui_col']), ('visible', 'gk_rbeetle_mc', 1),
            ('rotate', 'gk_rsweep_mc', round(C.UI_SPEED, 2)), ('visible', 'gkwave_mc', 1), ('goto', 'gkwave_mc', 1),
            ('colour', 'gkwave_mc', A['ui_col'] + 12)], True, 1))
    check('UI v1: his New_Var 58 read (UI_VAR 0x%08X: his MSC\'s gk_ui)' % C.UI_VAR,
          C.UI_VAR in [c[1] for c in e.calls if c[0] == 'getf'], True)
    angs = []
    for t in range(99):
        got, _k = frame(30)
        angs.append([c[2] for c in got if c[0] == 'rotate'][0])
    check('UI v1 spin, ready: 3.6 degrees every frame, a full turn in 100 frames, kept in 0 - 360 (frames 2 - 100)',
          angs, [round((C.UI_SPEED * (k + 2)) % 360.0, 2) for k in range(99)], tol=0.05)
    e.setw(A['ui_ang'], 0)
    got, _k = frame(450 * 1000 + 30)
    check('UI v1: the Parabeetle\'s cooldown (450 left): the beetle hidden, the sweep a quarter speed (0.9)',
          [c for c in got if c[1] in ('gk_rbeetle_mc', 'gk_rsweep_mc')],
          [('visible', 'gk_rbeetle_mc', 0), ('rotate', 'gk_rsweep_mc', round(C.UI_SPEED_CD, 2))])
    angs, beet = [], []
    for left in range(449, 0, -1):
        got, _k = frame(left * 1000 + 30)
        angs.append([c[2] for c in got if c[0] == 'rotate'][0])
        beet.append([c[2] for c in got if c[1] == 'gk_rbeetle_mc'][0])
    check('UI v1 spin, cooldown: 0.9 a frame for its whole 450 frames (a turn in 400), the beetle hidden every frame',
          (angs[::50], set(beet)), ([round((C.UI_SPEED_CD * (k + 2)) % 360.0, 2) for k in range(449)][::50], {0}), tol=0.05)
    a0 = angs[-1]
    got, _k = frame(30)
    check('UI v1: the cooldown over (0): the beetle shown again, the sweep at full speed from where it was',
          [c for c in got if c[1] in ('gk_rbeetle_mc', 'gk_rsweep_mc')],
          [('visible', 'gk_rbeetle_mc', 1), ('rotate', 'gk_rsweep_mc', round((a0 + C.UI_SPEED) % 360.0, 2))], tol=0.05)
    # the waveform's mapping
    rows = []
    for ch in (0, 19, 20, 39, 40, 59, 60, 79, 80, 99, 100, 119):
        e.setw(A['ui_t'], 0)
        got, _k = frame(ch)
        rows.append([c[2] for c in got if c[0] == 'goto'][0])
    check('UI v1 waveform: its level by the charge (charge x 6 / 120: 0 - 19 -> frames 1 - 6, ... 100 - 119 -> 31 - 36: the '
          'amplitude grows with it), phase 0 at its first count', rows,
          [C.ui_frame(ch, 1) for ch in (0, 19, 20, 39, 40, 59, 60, 79, 80, 99, 100, 119)])
    check('... = tools/gekkouga_ui_art.wave_index (the frames the art draws) + 1', rows,
          [1 + C.UI_LEVELS * C.UI_PHASES * 0 + ((ch * 6 // 120) * 6) for ch in (0, 19, 20, 39, 40, 59, 60, 79, 80, 99, 100, 119)])
    e.setw(A['ui_t'], 0)
    seq = []
    for t in range(60):
        got, _k = frame(70)
        seq.append([c[2] for c in got if c[0] == 'goto'][0])
    check('UI v1 waveform below full (70: level 3): gently animated: its phase a step every 8 frames (a wavelength in 48)',
          seq, [C.ui_frame(70, t + 1) for t in range(60)])
    check('... the frames 19 - 24 only (level 3), each held 8 frames', (sorted(set(seq)), seq[:7], seq[7:15]),
          (list(range(19, 25)), [19] * 7, [20] * 8))
    e.setw(A['ui_t'], 0)
    seq, cols = [], set()
    for t in range(50):
        got, _k = frame(120)
        seq.append([c[2] for c in got if c[0] == 'goto'][0])
        cols |= {c[2] for c in got if c[0] == 'colour' and c[1] == 'gkwave_mc'}
    check('UI v1 waveform at full (120: charged, the next smash releases): the rainbow frames 37 - 60, a new one every frame '
          '(very quick), looping every 24; drawn in its own colours (the full colour)',
          (seq, cols), ([37 + (t + 1) % 24 for t in range(50)], {A['ui_col'] + 24}))
    got, _k = frame(450 * 1000 + 120)
    check('UI v1: a full charge with the cooldown running: rainbow and the slow radar together (independent)',
          ([c[2] for c in got if c[0] == 'rotate'] != [], [c for c in got if c[1] == 'gk_rbeetle_mc'],
           [c[2] for c in got if c[0] == 'goto'][0] >= 37), (True, [('visible', 'gk_rbeetle_mc', 0)], True))
    got, _k = frame(999)
    check('UI v1: a charge word over 120 (not from his MSC) clamped to full', [c[2] for c in got if c[0] == 'goto'][0] >= 37, True)
    got, _k = frame(-5)
    check('UI v1: a negative word: read as 0 (ready, no charge)', [c for c in got if c[1] == 'gk_rbeetle_mc'],
          [('visible', 'gk_rbeetle_mc', 1)])
    # KO / reset: his MSC writes 0 (gk_pb_clear, gk_smash = 0): the panel follows the next frame
    frame(300 * 1000 + 120)
    e.setw(A['ui_t'], 0)
    got, _k = frame(0)
    check('UI v1: KO / reset (his MSC\'s word 0): the next frame the beetle back, the normal spin, the calm level-0 wave',
          ([c for c in got if c[1] == 'gk_rbeetle_mc'], [c for c in got if c[1] == 'gkwave_mc' and c[0] != 'visible']),
          ([('visible', 'gk_rbeetle_mc', 1)], [('goto', 'gkwave_mc', 1), ('colour', 'gkwave_mc', A['ui_col'] + 12)]))
    # only his panel: Little Mac's slot (2) carries the same clips and is never touched
    allc = []
    for w in (0, 450030, 120):
        allc += frame(w)[0]
    check('UI v1: only on his panel: no call on Little Mac\'s panel\'s radar / waveform (they stay as laid out: alpha 0)',
          [c for c in allc if str(c[1]).startswith('MAC')], [])
    # a panel without the clips (an older dmg.flx): nothing, no crash; without the waveform the radar still turns
    have['wave'] = False
    got, kept = frame(30)
    check('UI v1: no gkwave_mc: the radar as before, nothing on the wave', ([c[1] for c in got], kept),
          (['gkradar_mc', 'gkradar_mc', 'gk_rbeetle_mc', 'gk_rsweep_mc'], True))
    have['wave'], have['beetle'] = True, False
    got, kept = frame(30)
    check('UI v1: no gk_rbeetle_mc: the sweep and the waveform still', [c[1] for c in got],
          ['gkradar_mc', 'gkradar_mc', 'gk_rsweep_mc', 'gkwave_mc', 'gkwave_mc', 'gkwave_mc'])
    have['beetle'] = True
    e.setw(slot(0) + 0x5C, 0)
    got, kept = frame(30)
    check('UI v1: no root clip: nothing', (got, kept), ([], True))
    e.setw(slot(0) + 0x5C, root)
    e.setw(slot(2) + 0x5C, 0)
    if diag:
        for i in range(8):
            e.setw(A['ui_log'] + 4 * i, 0xFFFFFFFF)
        logs = []
        for w in (0, 0, 10, 25, 450025, 449025, 25, 120):
            frame(w)
            logs += [x[1:5] for x in e.osr_full if x[0] == A['gk_fui']]
        check('UI v1 diag: S4UI (slot, cooldown, charge, wave frame) when the cooldown starts / ends or the charge passes a '
              'sixth; not every frame', [x[:3] for x in logs],
              [(0, 0, 0), (0, 0, 25), (0, 450, 25), (0, 0, 25), (0, 0, 120)])


def burn2_checks(e, info, diag):
    """burn v2 (feature burn2): the burning fighters' fire (bfx_vic, from his burn_tick) and the fire trail article
    (kind TR_KIND: its tables, tr_claim from his requests, its contexts, its hits' burns with the trail row)"""
    lab, A, F, img = info['labels'], info['A'], info['feats'], info['img']
    tr = C.TR_ROW
    fl = C.burn_floor(F)
    check('burn v2: the trail row 0.25 %% every 15 frames for 180 = %.2f %%; shielded half the frames, raised to the floor: '
          '%.3f %% a tick x 6 = %.2f %%' % (C.burn_total(tr), C.burn_shield_damage(tr, fl), C.burn_total(tr, True, fl)),
          (round(C.burn_total(tr), 4), round(C.burn_total(tr, True, fl), 4)), (3.0, fl))
    if 'burn2' not in F:
        check('burn v2: without "burn2": no trail / fire code', ('tr_frame' in lab, 'bfx_vic' in lab), (False, False))
        return
    check('burn v2: its rows: burn v1\'s and the skeleton\'s, then the trail\'s (key 0x%X)' % C.TR_BURN_KEY,
          [struct.unpack('>I', bytes(e.mu.mem_read(A['bmoves'] + 20 * i, 4)))[0] for i in range(len(C.burn_moves(F)))],
          [m[0] for m in C.BURN_MOVES] + [C.TR_BURN_KEY] + ([C.SK_TOUCH_KEY] if 'sktouch' in F else []))
    if 'sktouch' in F:
        tr_ = C.SK_TOUCH_ROW
        fl_ = C.burn_floor(F)
        # one second of contact: a hit every 3 frames (SK_TOUCH_PERIOD), each an instance ticking its row
        per = 3
        hits = list(range(0, 60, per))
        dmg = sum(tr_[1] for h0 in hits for t in range(h0 + tr_[2], h0 + tr_[3] + 1, tr_[2]))
        alive = max(sum(1 for h0 in hits if h0 <= t < h0 + tr_[3]) for t in range(120))
        check('skeleton v1.5 contact burn: 0.35 %% every 6 frames for 60 = %.2f %% a touch; 1 s of contact (a touch every %d '
              'frames: 20) = %.1f %% (the user: ~70), at most %d instances at once (cap %d); shielded: %.3f %% a tick x %d = '
              '%.2f %% (the floor)' % (C.burn_total(tr_), per, dmg, alive, C.BURN_CAP, C.burn_shield_damage(tr_, fl_),
                                     C.burn_shield_frames(tr_) // tr_[2], C.burn_total(tr_, True, fl_)),
              (round(C.burn_total(tr_), 3), round(dmg, 1), alive <= C.BURN_CAP, round(C.burn_total(tr_, True, fl_), 3)),
              (3.5, 70.0, True, fl_))
    # ---- (1) the fire on a burning fighter
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    for kk in range(C.SLOTS * C.BURN_CAP):
        e.setw(A['btab'] + 16 * kk, 0)
    for i in range(C.SLOTS + C.SLOTS * C.TR_CTX):
        e.setw(A['bfx_lvl'] + 4 * i, 0)
    calls = []
    emvt = e.alloc(0x400, b'\0')
    emfn = e.alloc(4)
    e.setw(emvt + C.EM_MSC, emfn)

    def em(e_):
        ptr, n = e_.w(e_.r(4)), e_.w(e_.r(4) + 4)
        ws = [e_.w(ptr + 4 * i) for i in range(n)]
        if ws[0] == 0x2717:
            ws = ws[:3] + [round(struct.unpack('>f', struct.pack('>I', w))[0], 3) for w in ws[3:10]] + ws[10:]
        calls.append((e_.r(3), tuple(ws)))
    e.stub(emfn, em)
    gk = e.fighter(2)
    e.mu.mem_write(gk['f'] + 0x1E, b'\x04')
    vic = e.fighter(4)
    e.mu.mem_write(vic['f'] + 0x1E, b'\x04')
    vacc = e.w(vic['f'] + C.BASE_ACC)
    vem = e.alloc(0x10, b'\0')
    e.setw(vem, emvt)
    e.setw(vacc + C.F_EFFECT, vem)

    def put(n, owner=2):
        """victim 4's instances: n of (1000 frames, every 100, no damage), or a list of (frames left, interval, damage)"""
        ins = n if isinstance(n, list) else [(1000, 100, 0.0)] * n
        for kk in range(C.BURN_CAP):
            a = A['btab'] + (4 * C.BURN_CAP + kk) * 16
            if kk < len(ins):
                f_, iv, dmg = ins[kk]
                e.setw(a, f_)
                e.setw(a + 4, (iv << 16) | iv)
                e.setw(a + 8, owner)
                e.mu.mem_write(a + 12, struct.pack('>f', dmg))
            else:
                e.setw(a, 0)

    def frame(slot0=2, f=None):
        del calls[:]
        e.osr_full = []
        e.call(lab['burn_him'], (f or gk)['f'], slot0)
        return list(calls)
    if 'tiers' in F:
        tier_checks(e, A, put, frame, vem)
        if 'btint' in F:
            btint_checks(e, info, put, frame, vic)
    else:
        bfx_level_checks(e, A, put, frame, vem, gk)
    if diag:
        frame()
        put(1)
        frame()
        check('burn v2 diag: S4BF (victim 4, level 0 -> 1)', [x[1:4] for x in e.osr_full if x[0] == A['gk_fbf']], [(4, 0, 1)])
        put(0)
        frame()
    e.mu.mem_write(vic['f'] + 0x1E, b'\x00')
    put(2)
    check('burn v2: a victim no longer live: its level kept, no call', (frame(), e.w(A['bfx_lvl'] + 16)), ([], 0))
    put(0)
    frame()
    e.mu.mem_write(vic['f'] + 0x1E, b'\x04')
    burn2_trail_checks(e, info, diag, gk)


def tier_checks(e, A, put, frame, vem):
    """skeleton v1.3 (tiers): the fire on a burning fighter by tier (C.BFX_TIERS): its burns' count, remaining damage,
    strongest rate; a swap only when the tier changes"""
    ids = C.BFX_TIER_IDS
    spawn = lambda t: (vem, (0x2717, ids[t], 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0))   # noqa: E731
    end = lambda t, k: (vem, (0x2723, ids[t], k, k))                                     # noqa: E731
    rows = {m[0]: m for m in C.BURN_MOVES}

    def inst(row, left=None):
        _k, dmg, iv, frames = row
        return (frames if left is None else left, iv, dmg)
    nair, fair, smash, sk = rows[104], rows[105], rows[95], rows[C.SK_BURN_KEY]
    cases = [('one neutral air burn (3 %, 1 %/s)', [inst(nair)], 1),
             ('one forward air burn (5.4 %: over 4)', [inst(fair)], 2),
             ('two neutral air burns (count 2)', [inst(nair)] * 2, 2),
             ('one smash burn (4 %/s)', [inst(smash)], 3),
             ('four neutral air burns (count 4)', [inst(nair)] * 4, 3),
             ('the skeleton\'s explosion burn (6 %/s)', [inst(sk)], 4),
             ('the explosion burn nearly out (60 frames left: 6 %, still 6 %/s)', [inst(sk, 60)], 4),
             ('six neutral air burns (count 6)', [inst(nair)] * 6, 4),
             ('a forward air burn nearly out (20 frames: 0.6 %, 1.8 %/s: the rate)', [inst(fair, 20)], 2),
             ('three burns of 0.5 % every 15 frames, 90 frames left: 9 % between them, 2 %/s (remaining)',
              [(90, 15, 0.5)] * 3, 3)]
    check('burn tiers: the Python reference (bfx_tier) on each case',
          [C.bfx_tier(c[1]) for c in cases], [c[2] for c in cases])
    for what, ins, want in cases:
        put(0)
        frame()
        put(ins)
        got = frame()
        check('burn tiers: %s: tier %d, its own effect (0x%X) put on' % (what, want, ids[want]),
              (got, e.w(A['bfx_lvl'] + 16)), ([spawn(want)], want))
    put(0)
    frame()
    put([inst(nair)])
    frame()
    put([inst(nair)] * 2)
    check('burn tiers: 1 -> 2 burns: the tier-1 fire ended at once, the tier-2 one put on', frame(), [end(1, 1), spawn(2)])
    put([inst(nair, 120)] * 2)
    check('burn tiers: the 2 burns burning down (still tier 2): no swap', frame(), [])
    put([inst(nair, 120)] * 2 + [inst(sk)])
    check('burn tiers: + the explosion burn: tier 4 (2 -> 4)', frame(), [end(2, 1), spawn(4)])
    put([inst(nair)] * 9)
    check('burn tiers: 9 weak burns: still 4: nothing', frame(), [])
    put([inst(nair, 30)])
    check('burn tiers: one weak burn left: down to 1', frame(), [end(4, 1), spawn(1)])
    put(0)
    check('burn tiers: no burn left: the fire ended with a fade (0x2723 (id, 0, 0): its 15 frames), nothing put on',
          frame(), [end(1, 0)])


def btint_checks(e, info, put, frame, vic):
    """burn tint v1 (feature btint): the burning victim's overlay (ColorBlendModule slot BTINT_SLOT) and its outline (an
    Outline_Shell table entry) by its fire's tier, the fade, the KO, a reset, a command's outline left alone"""
    lab, A = info['labels'], info['A']
    rows = {m[0]: m for m in C.BURN_MOVES}
    nair, fair, sk = rows[104], rows[105], rows[C.SK_BURN_KEY]
    inst = lambda r: (r[3], r[2], r[1])                                 # noqa: E731
    vacc = e.w(vic['f'] + C.BASE_ACC)
    cvt = e.alloc(0x100, b'\0')
    cset, cclr = e.alloc(4), e.alloc(4)
    e.setw(cvt + 0x4C, cset)
    e.setw(cvt + C.COLOUR_CLEAR, cclr)
    cbm = e.alloc(0x100, b'\0')
    e.setw(cbm, cvt)
    e.setw(vacc + C.W_COLOUR, cbm)
    calls = []
    rd = lambda a, n: [round(x, 4) for x in struct.unpack('>%df' % n, bytes(e.mu.mem_read(a, 4 * n)))]   # noqa: E731
    e.stub(cset, lambda e_: calls.append(('set', tuple(rd(e_.r(4), 4)), e_.r(5), e_.r(6))))
    e.stub(cclr, lambda e_: calls.append(('clear', e_.r(4))))
    mm = e.alloc(0x40, b'\0')
    inst_obj = e.alloc(0x100, b'\0')
    e.setw(mm + 0xC, inst_obj)
    e.setw(vacc + 0x3C, mm)
    stm = e.alloc(0x60, b'\0')
    e.setw(vacc + C.F_STATUS, stm)
    os_g = 0x04BE5D10

    def ent():
        for i in range(C.OS_N):
            a = C.OS_TAB + C.OS_ENT * i
            if e.w(a) == vacc:
                return a
        return None

    def shell():
        a = ent()
        if a is None:
            return None
        return (e.w(a + 4) == inst_obj, e.w(a + 8), tuple(rd(a + 0x1C, 3)), rd(a + 0x28, 1)[0], rd(a + 0x2C, 1)[0], e.w(os_g))

    def want_shell(tier, fade=C.BTINT_FADE):
        _t, sh = C.btint_ref(tier, fade)
        return (True, 2, tuple(round(x, 4) for x in sh[:3]), round(sh[3], 4), round(sh[4], 4), 1)

    def want_set(tier, fade=C.BTINT_FADE):
        t, _sh = C.btint_ref(tier, fade)
        return ('set', tuple(round(x, 4) for x in t), C.BTINT_SLOT, 0)

    def step(ins=None):
        if ins is not None:
            put(ins)
        del calls[:]
        frame()
        return list(calls)
    for i in range(C.OS_N * C.OS_ENT // 4):
        e.setw(C.OS_TAB + 4 * i, 0)
    e.setw(os_g, 0)
    for _ in range(C.BTINT_FADE + 2):
        step(0)
    check('burn tint: the colour table (the user: orange -> hot red, a faint red outline growing a little): tiers 1 - 4',
          [C.btint_ref(t, C.BTINT_FADE) for t in (1, 2, 3, 4)],
          [(C.BTINT_TINT[t], C.BTINT_SHELL[t]) for t in (1, 2, 3, 4)])
    check('burn tint: no burn: no overlay, no outline', (step(0), shell()), ([], None))
    for tier, ins, what in ((1, [inst(nair)], 'a neutral air burn'), (2, [inst(fair)], 'a forward air burn'),
                            (4, [inst(sk)], 'the explosion burn')):
        got = step(ins)
        check('burn tint: %s (tier %d): its overlay in slot %d (%s), its outline entry (held, faint red, alpha %.2f, '
              'width %.2f px; the table\'s count 1)' % (what, tier, C.BTINT_SLOT, C.BTINT_TINT[tier], C.BTINT_SHELL[tier][3],
                                                       C.BTINT_SHELL[tier][4]),
              (got, shell()), ([want_set(tier)], want_shell(tier)))
    check('burn tint: ... every frame while it burns (the game\'s own overlays may clear the slot)', step(), [want_set(4)])
    a0 = ent()
    fades = []
    for f in range(C.BTINT_FADE - 1, 0, -1):
        got = step(0)
        fades.append((got == [want_set(4, f)], shell() == want_shell(4, f)))
    check('burn tint: the burns end: overlay and outline fade over %d frames (the fire\'s fade), same entry' % C.BTINT_FADE,
          (fades, ent() == a0), ([(True, True)] * (C.BTINT_FADE - 1), True))
    check('burn tint: ... then off: the slot cleared (vt +0x%X(%d)), the outline entry freed (count 0)' % (C.COLOUR_CLEAR,
          C.BTINT_SLOT), (step(0), ent(), e.w(os_g)), ([('clear', C.BTINT_SLOT)], None, 0))
    check('burn tint: ... and nothing after', step(0), [])
    # a command's outline (Supamario's Ultra Instinct glow): left alone, the tint still shown
    cmd = C.OS_TAB + C.OS_ENT * 5
    e.setw(cmd, vacc)
    e.setw(cmd + 4, inst_obj)
    e.setw(cmd + 8, 2)
    e.mu.mem_write(cmd + 0x1C, struct.pack('>5f', 0.8, 0.9, 1.0, 1.0, 4.0))
    e.setw(os_g, 1)
    got = step([inst(nair)])
    check('burn tint: an outline a command put on it (another entry of its accessor): left as it is; its overlay still on',
          (got, rd(cmd + 0x1C, 5), e.w(os_g)), ([want_set(1)], [0.8, 0.9, 1.0, 1.0, 4.0], 1))
    e.setw(cmd, 0)
    e.setw(cmd + 8, 0)
    e.setw(os_g, 0)
    step()
    a1 = ent()
    e.mu.mem_write(a1 + 0x2C, struct.pack('>f', 6.0))          # a command took our entry over (its width)
    step()
    check('burn tint: our entry taken over by a command (its width changed): no longer written, nor freed at the end',
          (rd(a1 + 0x2C, 1), e.w(A['bti_st'] + 16 * 4 + 8)), ([6.0], 0))
    for _ in range(C.BTINT_FADE + 1):
        step(0)
    check('burn tint: ... its end: the overlay cleared, that entry kept (a command\'s)', ent() == a1, True)
    e.setw(a1, 0)
    e.setw(a1 + 8, 0)
    # a KO: off at once
    step([inst(sk)])
    e.setw(stm + C.ST_KIND, C.ST_DEAD)
    got = step()
    check('burn tint: KO\'d (Dead): off at once (its burns cleared, the slot cleared, the entry freed)',
          (got, ent()), ([('clear', C.BTINT_SLOT)], None))
    check('burn tint: ... dead the next frame: nothing again', step(), [])
    e.setw(stm + C.ST_KIND, 0)
    # a reset (gk_clear: tier 0, fade -1): off the next frame
    step([inst(nair)])
    e.setw(A['bti_st'] + 16 * 4, 0)
    e.setw(A['bti_st'] + 16 * 4 + 4, 0xFFFFFFFF)
    got = step(0)
    check('burn tint: after a match / training reset (gk_clear: tier 0, fade -1): off the next frame, no fade',
          (got, ent()), ([('clear', C.BTINT_SLOT)], None))
    # only the first live Greninja steps it
    e.setw(A['bti_st'] + 16 * 4 + 4, 0)
    put([inst(nair)])
    gk0 = e.fighter(0)
    e.mu.mem_write(gk0['f'] + 0x1E, b'\x04')
    del calls[:]
    frame()
    check('burn tint: a Greninja in an earlier slot (0): slot 2\'s burn_tick leaves the tint to his', calls, [])
    e.mu.mem_write(gk0['f'] + 0x1E, b'\x00')
    for _ in range(C.BTINT_FADE + 2):
        step(0)


def bfx_level_checks(e, A, put, frame, vem, gk):
    """burn v2 - aerial chain v1 (no tiers): one fire, scaled by the count"""
    put(1)
    c1 = frame()
    spawn = lambda sz: (vem, (0x2717, C.BFX_ID, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, sz, 0))   # noqa: E731
    check('burn v2: a victim with one burn: its fire put on it (its EffectModule\'s MSC handler: 0x2717 (0x%X, joint 0, '
          'no offset, size 1.0, 0): following its joint 0)' % C.BFX_ID, (c1, e.w(A['bfx_lvl'] + 16)), ([spawn(1.0)], 1))
    check('burn v2: ... the next frame: nothing (shown)', frame(), [])
    put(3)
    put(2, 6) if False else None
    for kk in (1, 2):
        e.setw(A['btab'] + (4 * C.BURN_CAP + kk) * 16 + 8, 6)       # two of another Greninja's (slot 7)
    check('burn v2: 3 burns (anyone\'s): the fire ended at once (0x2723 (id, 1, 1)) and put on again at 1.3',
          frame(), [(vem, (0x2723, C.BFX_ID, 1, 1)), spawn(1.3)])
    put(9)
    check('burn v2: 9 burns: level 5 (the most): 1.6', frame()[-1:], [spawn(1.6)])
    put(12)
    check('burn v2: 12 burns: still level 5: nothing', frame(), [])
    gk2 = e.fighter(6)
    e.mu.mem_write(gk2['f'] + 0x1E, b'\x04')
    check('burn v2: another Greninja\'s burn_tick the same frame: nothing again (the level shown is shared)',
          frame(6, gk2), [])
    put(0)
    c0 = frame()
    check('burn v2: no burn left: the fire ended with a fade (0x2723 (id, 0, 0)), nothing put on', c0,
          [(vem, (0x2723, C.BFX_ID, 0, 0))])


def burn2_trail_checks(e, info, diag, gk):
    lab, A, F, img = info['labels'], info['A'], info['feats'], info['img']
    # ---- (2) the fire trail article: its tables
    T = info['T']
    k = C.TR_KIND - W.OLD_N
    check('trail tables: name / folder "firetrail", owner "gekkouga"',
          [e.cstr(e.w(T[nm] + 4 * C.TR_KIND)) for nm in ('owner', 'name', 'folder')], ['gekkouga', 'firetrail', 'firetrail'])
    check('trail tables: base kind Mario\'s pump, its own singleton / row (the clone\'s)',
          (e.w(T['bt'] + 4 * k), e.w(T['st'] + 4 * k), e.w(T['rt'] + 4 * k) + W.MODULE_TABLE & 0xFFFFFFFF,
           [e.w(A['tr_row'] + 4 * j) for j in range(28)] == [e.w(A['w_row'] + 4 * j) for j in range(28)]),
          (C.ATTACK_BASE, A['tr_single'], A['tr_row'], True))
    u16 = e.mu.mem_read(T['u16'] + 2 * C.TR_KIND, 2)
    bun = img.h(W.STATIC_TABLES[2][1] + 2 * C.CLONE_BASE)
    check('trail tables: u16 flags as the skeleton\'s (c00 only, loaded with him)', struct.unpack('>H', bytes(u16))[0],
          bun & ~(C.CATEGORY_BITS | 0x10))
    e.call(e.w(T['dt'] + 4 * k))
    d = e.r(3)
    mi = e.w(d + 8)
    nm_ = C.tr_motions(F)
    check('trail descriptor: a bunshin copy, %d motions (the hydrant\'s hash: forward / up / down%s)' % (
          nm_, ' / ice detonation v1\'s blast' if nm_ == 4 else ''),
          (d, e.w(mi + 4), [e.w(e.w(mi) + 8 * i) for i in range(nm_)]), (A['tr_desc'], nm_, [C.SK_MOTION] * nm_))
    vt = A['tr_vt']
    check('trail singleton: +0x34 the skeleton\'s start (its VARs 0), +0x94 tr_94, +0xAC the skeleton\'s hit method (not '
          'removed by its hits)', (e.w(A['tr_single']), e.w(vt + 0x34), e.w(vt + 0x94), e.w(vt + W.HIT_METHOD)),
          (vt, lab['sk_start'], lab['tr_94'], lab['sk_hit']))
    lst = e.w(A['gk_desc'] + 8)
    trn = C.TR_MAX + (C.ICE_SLOTS_EXTRA if 'ice' in F else 0)
    check('his article list: article 9 the fire trails (0x1A3, %d at once%s)' % (trn, ': ice detonation v1, + 2 for '
          'blasts' if 'ice' in F else ''), [e.w(e.w(lst) + 16 * 9 + 4 * j) for j in range(4)], [C.TR_KIND, trn, 0, 0])
    # ---- its claim, contexts and burns
    sv = {}
    svt = e.alloc(0x100, b'\0')
    g, s_ = e.alloc(4), e.alloc(4)
    e.setw(svt + 0x44, g)
    e.setw(svt + 0x4C, s_)
    cur = {}
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(cur['sv'].get(e_.r(4), 0.0))))

    def sset(e_):
        cur['sv'][e_.r(4)] = round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)
    e.stub(s_, sset)

    def trail():
        w = e.alloc(0x40, b'\0')
        acc = e.alloc(0x100, b'\0')
        wm = e.alloc(0x10, b'\0')
        e.setw(wm, svt)
        e.setw(acc + C.W_WORK, wm)
        am = e.alloc(0x60, b'\0')
        ents = e.alloc(C.ENT_SIZE * 2, b'\0')
        hdr = e.alloc(0x10, b'\0')
        e.setw(hdr + 4, hdr)
        e.setw(ents + C.ENT_LOG, hdr)
        hdr2 = e.alloc(0x10, b'\0')
        e.setw(hdr2 + 4, hdr2)
        e.setw(ents + C.ENT_SIZE + C.ENT_LOG, hdr2)
        e.setw(am + C.AM_ENTS, ents)
        e.setw(am + C.AM_COUNT, 2)
        e.setw(acc + C.W_ATTACK, am)
        e.setw(w + C.W_ACC, acc)
        return dict(w=w, sv={}, log=hdr)

    def tframe(t):
        cur['sv'] = t['sv']
        e.osr_full = []
        e.call(lab['tr_frame'], t['w'])

    def tvars(t):
        return [t['sv'].get(0x0F000300 + i, 0.0) for i in range(6)]

    def ttl(slot0):
        return [e.w(A['tr_ttl'] + 4 * (slot0 * C.TR_CTX + i)) for i in range(C.TR_CTX)]
    V = C.GK_VAR_TR
    e.vars = {V: 1.0, V + 1: 30.0, V + 2: 5.0, V + 3: -1.0, V + 4: 3.0, V + 5: 60.0, V + 6: 6.0, V + 7: 1.0}
    other = e.fighter(1)
    e.setw(other['f'] + 4, 0x1)                          # slot 2: Mario (his VARs are the same dict: not a Greninja)
    e.mu.mem_write(other['f'] + 0x1E, b'\x04')
    ctx0 = C.TR_CTX0 + 2 * C.TR_CTX
    e.mu.mem_write(A['bproc'] + ctx0 * C.BURN_ENTS, b'\x07' * C.BURN_ENTS)
    ta, tb, tc = trail(), trail(), trail()
    tframe(ta)
    check('trail claim: the first trail takes his request 0 (forward smash at (30, 5), way -1): VAR_0 his slot 3, VAR_1-4 '
          'the request, VAR_5 his first context; his request 0 cleared (request 1 kept)',
          (tvars(ta), e.vars.get(V), e.vars.get(V + 4)), ([3.0, 1.0, 30.0, 5.0, -1.0, 1.0], 0.0, 3.0))
    check('trail claim: its context kept (%d frames) and its processed counts from 0' % C.TR_TTL,
          (ttl(2)[:2], bytes(e.mu.mem_read(A['bproc'] + ctx0 * C.BURN_ENTS, C.BURN_ENTS))), ([3, 0], bytes(C.BURN_ENTS)))
    if diag:
        check('trail diag: S4TR (owner 3, type 1, x 30, y 5, context 1)',
              [x[1:6] for x in e.osr_full if x[0] == A['gk_ftr']], [(3, 1, 30, 5, 1)])
    tframe(tb)
    check('trail claim: the second takes request 1 (down smash at (60, 6), way 1), his second context',
          (tvars(tb), e.vars.get(V + 4), ttl(2)[:2]), ([3.0, 3.0, 60.0, 6.0, 1.0, 2.0], 0.0, [3, 3]))
    tframe(tc)
    check('trail claim: a third with no request left: unclaimed (VAR_0 0)', tvars(tc)[0], 0.0)
    e.vars = {}
    e.call(lab['burn_him'], gk['f'], 2)
    e.call(lab['burn_him'], gk['f'], 2)
    tframe(ta)
    check('trail contexts: his frames count them down (3 -> 1), a running trail\'s frame renews its own (3)',
          ttl(2)[:2], [3, 1])
    e.call(lab['burn_him'], gk['f'], 2)
    e.call(lab['burn_him'], gk['f'], 2)
    e.call(lab['burn_him'], gk['f'], 2)
    check('trail contexts: a trail gone (no frame of its own) frees its context', ttl(2)[:2], [0, 0])
    # its hits
    for kk in range(C.SLOTS * C.BURN_CAP):
        e.setw(A['btab'] + 16 * kk, 0)
    tframe(ta)
    n = e.alloc(0x30, b'\0')
    e.setw(n + C.NODE_OBJ, (4 << 16) | 0x11)
    e.mu.mem_write(n + C.NODE_TYPE, b'\x01')
    e.setw(n + 4, ta['log'])
    e.setw(ta['log'] + 4, n)
    e.setw(ta['log'] + 8, 1)
    tframe(ta)

    def insts(v):
        out = []
        for kk in range(C.BURN_CAP):
            a = A['btab'] + (v * C.BURN_CAP + kk) * 16
            if e.w(a):
                out.append((e.w(a), e.w(a + 4) & 0xFFFF, e.w(a + 8), round(struct.unpack('>f', struct.pack('>I', e.w(a + 12)))[0], 4)))
        return out
    check('trail hit: a burn on the victim (slot 5) for him (owner 2): 180 frames, every 15, 0.25 %', insts(4), [(180, 15, 2, 0.25)])
    tframe(ta)
    check('trail hit: the same log node: no second', len(insts(4)), 1)
    n2 = e.alloc(0x30, b'\0')
    e.setw(n2 + C.NODE_OBJ, (4 << 16) | 0x11)
    e.mu.mem_write(n2 + C.NODE_TYPE, b'\x02')
    e.setw(n2 + 4, ta['log'])
    e.setw(n + 4, n2)
    e.setw(ta['log'] + 8, 2)
    tframe(ta)
    tsd = round(C.burn_shield_damage(C.TR_ROW, C.burn_floor(F)), 4)
    check('trail hit: its re-hit on a shield: 90 frames, %s %% a tick (35 %% raised to the %g %% floor)' % (tsd, C.burn_floor(F)),
          insts(4)[1:], [(90, 15, 2, tsd)])
    # contexts run out
    for i in range(C.SLOTS * C.TR_CTX):
        e.setw(A['tr_ttl'] + 4 * i, 0)
    e.vars = {V: 2.0, V + 1: 0.0, V + 2: 0.0, V + 3: 1.0}
    ts = []
    for i in range(C.TR_CTX + 1):
        t = trail()
        e.vars[V] = 2.0
        tframe(t)
        ts.append((tvars(t)[0], tvars(t)[5]))
    check('trail contexts: %d trails at once each its own (1 - %d); one more: claimed with none (VAR_5 0: no burns)'
          % (C.TR_CTX, C.TR_CTX), ts, [(3.0, float(i + 1)) for i in range(C.TR_CTX)] + [(3.0, 0.0)])
    for i in range(C.SLOTS * C.TR_CTX):
        e.setw(A['tr_ttl'] + 4 * i, 0)
    e.vars = {}


def skdist_checks(e, info):
    """skeleton v1.6 (feature skdist): his slot 13's side special hold advance (the game's own words 0x02EEEB84 -
    0x02EEEC08, run in unicorn): the shadow's distance (instance float 0x35) + 0x0600000B (1.2) a frame, capped at
    C.SK_DIST (36) instead of his vl max distance 0x0600000C (70)"""
    from unicorn.ppc_const import UC_PPC_REG_FPR31
    if 'skdist' not in info['feats']:
        check('skdist off: his slot 13\'s cap loads are the game\'s (+0x30 of his float params)',
              [e.w(a) for a, _o, _t, _n in C.SK_DIST_PATCH], [o for _a, o, _t, _n in C.SK_DIST_PATCH])
        return
    fl = e.alloc(0x200, b'\0')                       # his instance floats
    fp = e.alloc(0x40, b'\0')                        # his float params (category 6): +0x2C speed, +0x30 max
    e.mu.mem_write(fp + 0x2C, struct.pack('>2f', 1.2, 70.0))
    cat0 = e.alloc(0x10, b'\0')
    e.setw(cat0 + 4, fl)
    par = e.alloc(0x10, b'\0')
    e.setw(par + 4, fp)
    wm8 = e.alloc(0x20, b'\0')
    e.setw(wm8, cat0)
    e.setw(wm8 + 0x18, par)
    acc = e.alloc(0x7400, b'\0')
    rate = e.alloc(0x20, b'\0')
    e.setw(rate + 0x1C, 1)
    e.setw(acc + 0x7304, rate)
    gs = e.alloc(8, b'\0')
    e.mu.mem_write(gs + 4, struct.pack('>f', 1.0))
    e.setw(0x102F6C04, gs)
    st = e.alloc(0x60, b'\0')
    e.setw(st + 0x48, 0x153)
    got = []
    for d in (2.0, 9.2, 34.0, 35.5, 36.0, 50.0):
        e.mu.mem_write(fl + 0xD4, struct.pack('>f', d))
        for r, v in ((7, wm8), (8, cat0), (26, acc), (30, st), (27, st)):
            e.mu.reg_write(REGS[r], v)
        e.mu.reg_write(UC_PPC_REG_FPR31, f2d(1.0))
        e.call(0x02EEEB84, until=0x02EEEC0C)
        got.append(round(struct.unpack('>f', bytes(e.mu.mem_read(fl + 0xD4, 4)))[0], 3))
    check('skeleton v1.6 (skdist): the hold\'s advance from 2 / 9.2 / 34 / 35.5 / 36 / 50: + 1.2 a frame, capped at '
          'SK_DIST %.0f (the vl max 70 no longer read); at or past it unchanged' % C.SK_DIST, got,
          [3.2, 10.4, 35.2, 36.0, 36.0, 50.0])
    check('skeleton v1.6 (skdist): its cap in the cave = SK_DIST', round(struct.unpack('>f', bytes(e.mu.mem_read(
        info['A']['sk_dist'], 4)))[0], 3), C.SK_DIST)


def shalf_checks(e, info):
    """smash tune v1 (feature shalf): SH_HOOK (the shield hit's `fmadds f8, f29, f28, f13`, the pending shield damage before
    the 1.19 multiplier) -> sh_half, run from the hooked word to SH_BACK on fake objects: a Greninja's attack (his own:
    a fighter id; a clone / his trail: a weapon id whose TeamModule owner is his) in a smash motion (95 / 99 / 101) or
    with the trail's Type (attack data +0x55 = SH_TYPE): f8 x 0.5; anything else (another move, another fighter's, an
    unknown / dead object) the game's f8; the registers the caller keeps (r14 - r31, f28 / f29, r1) as they were"""
    from unicorn.ppc_const import UC_PPC_REG_FPR8, UC_PPC_REG_FPR13, UC_PPC_REG_FPR28, UC_PPC_REG_FPR29
    if 'shalf' not in info['feats']:
        check('shalf off: the shield damage add is the game\'s', '%08X' % e.w(C.SH_HOOK), '%08X' % C.SH_ORIG)
        return
    lab = info['labels']
    check('shalf: the shield damage add (0x%08X) -> b sh_half' % C.SH_HOOK, K.branch_target(C.SH_HOOK, e.w(C.SH_HOOK)),
          lab['sh_half'])
    mgr = e.alloc(0x40, b'\0')
    e.setw(C.SH_MANAGER, mgr)
    recs = {}
    looked = []

    def lookup(e_):
        looked.append((e_.r(3), e_.r(4)))
        return recs.get(e_.r(4), 0)
    e.stub(C.SH_LOOKUP, lookup)
    owners = {}
    team_fn = e.alloc(4)

    def team(e_):
        return owners.get(e_.r(3), 0x50000000)
    e.stub(team_fn, team)
    team_vt = e.alloc(0x80, b'\0')
    e.setw(team_vt + 0x64, team_fn)

    def obj(oid, motion, live=4, owner=None):
        acc = e.alloc(0x100, b'\0')
        tm = e.alloc(0x20, b'\0')
        e.setw(tm, team_vt)
        e.setw(acc + C.TEAM_MOD, tm)
        mm = e.alloc(0x60, b'\0')
        e.setw(mm + C.MM_KIND, motion)
        e.setw(acc + C.W_MOTION, mm)
        rec = e.alloc(0x40, b'\0')
        e.setw(rec, oid)
        e.setw(rec + 0xC, acc)
        e.mu.mem_write(rec + 0x1E, bytes([live]))
        recs[oid] = rec
        if owner is not None:
            owners[tm] = owner
        return acc
    him = e.fighter(2)
    e.mu.mem_write(him['f'] + 0x1E, b'\x04')
    other = e.fighter(5)
    e.mu.mem_write(other['f'] + 0x1E, b'\x04')
    e.setw(other['f'] + 4, 0x3)                      # Mario
    gk_id, mario_id = 0x00020000, 0x00050000
    data = e.alloc(0x68, b'\0')
    ev = e.alloc(0x40, b'\0')
    col = e.alloc(0x40, b'\0')
    e.setw(ev + 0x10, col)

    def run(attacker, damage, sd=0.0, typ=0xA):
        e.setw(col + 0x18, attacker)
        e.mu.mem_write(data + 0x55, bytes([typ]))
        for i in range(14, 32):
            e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        e.mu.reg_write(REGS[26], data)
        e.mu.reg_write(REGS[30], ev)
        e.mu.reg_write(UC_PPC_REG_FPR29, f2d(damage))
        e.mu.reg_write(UC_PPC_REG_FPR28, f2d(1.0))
        e.mu.reg_write(UC_PPC_REG_FPR13, f2d(sd))
        e.mu.reg_write(UC_PPC_REG_FPR8, f2d(-1.0))
        e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        e.call(C.SH_HOOK, until=C.SH_BACK)
        kept = all(e.r(i) == 0x5A5A0000 + i for i in range(14, 32) if i not in (26, 30)) and e.r(26) == data and \
            e.r(30) == ev and e.mu.reg_read(UC_PPC_REG_1) == 0x70000000 + 0xF0000 and \
            round(d2f(e.mu.reg_read(UC_PPC_REG_FPR29)), 3) == round(damage, 3) and \
            d2f(e.mu.reg_read(UC_PPC_REG_FPR28)) == 1.0
        return round(d2f(e.mu.reg_read(UC_PPC_REG_FPR8)), 4), kept
    acc_him = obj(gk_id, 95)
    got = []
    for mk in (95, 99, 101, 104, 105, 0x50):
        e.setw(e.w(acc_him + C.W_MOTION) + C.MM_KIND, mk)
        got.append(run(gk_id, 14.0))
    check('shalf: his attack on a shield, 14 %: forward / up / down smash (motions 95 / 99 / 101) 7.0 (x 0.5); neutral / '
          'forward air, a jab (104 / 105 / 0x50) 14.0 (the game\'s); the caller\'s registers kept',
          got, [(7.0, True)] * 3 + [(14.0, True)] * 3)
    e.setw(e.w(acc_him + C.W_MOTION) + C.MM_KIND, 95)
    check('shalf: the shield damage field added in (10 % + 4: 14 -> 7) and an uncharged up smash hit (5 %: 2.5)',
          [run(gk_id, 10.0, 4.0)[0], run(gk_id, 5.0)[0]], [7.0, 2.5])
    obj(mario_id, 95)
    check('shalf: another fighter (Mario, kind 3) in his motion 95: 14.0', run(mario_id, 14.0)[0], 14.0)
    clone_id, trail_id, foe_trail = 0x10004000, 0x10007000, 0x10009000
    acc_cl = obj(clone_id, 99, owner=gk_id)
    obj(trail_id, 0, owner=gk_id)
    obj(foe_trail, 0, owner=mario_id)
    got = [run(clone_id, 11.0)[0]]
    e.setw(e.w(acc_cl + C.W_MOTION) + C.MM_KIND, 104)
    got.append(run(clone_id, 11.0)[0])
    got += [run(trail_id, 0.1, typ=C.SH_TYPE)[0], run(trail_id, 0.1, typ=9)[0], run(foe_trail, 0.1, typ=C.SH_TYPE)[0]]
    check('shalf: a clone (a weapon owned by him) in his up smash 11 -> 5.5, in his neutral air 11; his trail (Type 0x16) '
          '0.1 -> 0.05, Type 9 0.1; a weapon of Mario\'s with Type 0x16 0.1', got, [5.5, 11.0, 0.05, 0.1, 0.1])
    obj(0x0002FFFF, 95, live=2)
    check('shalf: an attacker not found (no record: 14.0), not live (+0x1E 2: 14.0), no collision record (14.0)',
          [run(0x00020099, 14.0)[0], run(0x0002FFFF, 14.0)[0]], [14.0, 14.0])
    e.setw(ev + 0x10, 0)
    check('shalf: ... no collision record on the event: 14.0', run(gk_id, 14.0)[0], 14.0)
    e.setw(ev + 0x10, col)
    check('shalf: the lookup called with the battle object manager and the attacker\'s id', looked[0], (mgr, gk_id))


def bgrav_checks(e, info, diag):
    """bgrav (the user: "make it so Greninja has his normal gravity and fall speed in burnout"): bg_set's Gravity_Set entry
    (the base exe's GS table: Mode 1, gravity x BG_RATE^2, max fall x BG_RATE) and his fast-fall speed (work float 0x24
    = BG_RATE x param 0x0300001B) while the burnout's slow is on, both cleared when it ends; and, with the slow taken as
    one kinetic step every BG_RATE frames, his fall per real frame against his own (the game's update's formula)"""
    from unicorn.ppc_const import UC_PPC_REG_FPR1 as F1
    lab, F = info['labels'], info['feats']
    if 'bgrav' not in F:
        check('bgrav off: no bg_set', 'bg_set' in lab, False)
        return
    gk = e.fighter(None)
    acc = e.w(gk['f'] + C.BASE_ACC)
    wm = e.alloc(0x20, b'\0')
    vt = e.alloc(0x100, b'\0')
    e.setw(wm, vt)
    g, s_ = e.alloc(4), e.alloc(4)
    e.setw(vt + 0x44, g)
    e.setw(vt + 0x4C, s_)
    e.setw(acc + 0x28, wm)
    stm = e.alloc(0x60, b'\0')
    e.setw(acc + 0x20, stm)
    DIVE = 2.2
    sv = {}
    e.stub(g, lambda e_: e_.mu.reg_write(F1, f2d(DIVE if e_.r(4) == 0x0300001B else 0.0)))
    e.stub(s_, lambda e_: sv.__setitem__(e_.r(4), round(d2f(e_.mu.reg_read(F1)), 4)))
    for i in range(C.GS_N * 8):
        e.setw(C.GS_TABLE + 4 * i, 0)
    e.setw(C.GS_TABLE, 0x12345678)                     # another fighter's entry (kept)
    ent = lambda: [(i, e.w(C.GS_TABLE + 0x20 * i + 4), round(struct.unpack('>f', struct.pack('>I', e.w(C.GS_TABLE + 0x20 * i + 8)))[0], 4),   # noqa: E731
                    round(struct.unpack('>f', struct.pack('>I', e.w(C.GS_TABLE + 0x20 * i + 12)))[0], 4), e.w(C.GS_TABLE + 0x20 * i + 16))
                   for i in range(C.GS_N) if e.w(C.GS_TABLE + 0x20 * i) == acc]
    e.call(lab['bg_set'], gk['f'], 2, 0)
    e.call(lab['bg_set'], gk['f'], 2, 1)
    on = (ent(), sv.get(0x24))
    check('bgrav: the burnout\'s slow on: his Gravity_Set entry (the base exe\'s table 0x%08X, the first free: 1; Mode 1 '
          'multipliers: gravity x %g, max fall x %g; made once, re-made each frame: a status change clears it) and his fast '
          'fall (work float 0x24, which the game\'s gravity update takes over param 0x0300001B) = %g x his %g'
          % (C.GS_TABLE, C.BG_RATE ** 2, C.BG_RATE, C.BG_RATE, DIVE), on,
          ([(1, stm, C.BG_RATE ** 2, C.BG_RATE, 1)], round(C.BG_RATE * DIVE, 4)))
    sv.clear()
    e.call(lab['bg_set'], gk['f'], 0, 1)
    check('bgrav: the burnout over (the slow off): his entry cleared (another fighter\'s kept), work float 0x24 back to 0',
          (ent(), sv.get(0x24), e.w(C.GS_TABLE)), ([], 0.0, 0x12345678))
    sv.clear()
    e.call(lab['bg_set'], gk['f'], 0, 0)
    check('bgrav: not in the burnout (and not before): nothing written', sv, {})
    e.setw(C.GS_TABLE, 0)
    # the fall, real frame by real frame (the gravity update: v += -g down to -max; fast fall v = -dive; the slow: one
    # step every BG_RATE frames, the position moving by v each step)
    G, MX = 0.09, 1.65
    n = int(C.BG_RATE)

    def fall(g_, mx, frames, step, dive=None):
        v, y, out = 0.0, 0.0, []
        for f in range(frames):
            if f % step == 0:
                v = -dive if dive else max(v - g_, -mx)
                y += v
            out.append(y)
        return out
    norm = fall(G, MX, 120, 1)
    slow = fall(G, MX, 120, n)
    comp = fall(G * C.BG_RATE ** 2, MX * C.BG_RATE, 120, n)
    vmax = lambda ys, k: round((ys[-1] - ys[-1 - k]) / k, 3)   # noqa: E731
    check('bgrav: falling 120 frames from rest (gravity %g, max fall %g): his own %.3f a frame at most; slowed (a step every '
          '%d frames) %.3f, %.0f %% of the drop; with bgrav\'s values %.3f, %.0f %% (within the step\'s quantisation); a fast '
          'fall (%g): his own %.2f, slowed %.2f, with bgrav %.2f' % (
              G, MX, -vmax(norm, n), n, -vmax(slow, n), 100 * slow[-1] / norm[-1], -vmax(comp, n), 100 * comp[-1] / norm[-1],
              DIVE, -vmax(fall(0, 0, 40, 1, DIVE), n), -vmax(fall(0, 0, 40, n, DIVE), n),
              -vmax(fall(0, 0, 40, n, DIVE * C.BG_RATE), n)),
          (vmax(comp, n) == vmax(norm, n), abs(comp[-1] / norm[-1] - 1) < 0.03, vmax(slow, n) == round(vmax(norm, n) / n, 3),
           vmax(fall(0, 0, 40, n, DIVE * C.BG_RATE), n) == vmax(fall(0, 0, 40, 1, DIVE), n)), (True, True, True, True))


CB_SET, CB_CLEAR, CB_PRIO, CB_PICK, CB_INIT = 0x02C1A12C, 0x02C1A110, 0x02C1A278, 0x02C1A288, 0x02C1A0C4   # the game's


def render_checks(e, lab, A, N, fl, put, hit, frame, st, vacc):
    """ice2: the countdown against the game's own ColorBlendModule code (vt +0x4C set 0x02C1A12C, +0x44 clear, +0x8C
    priority 0x02C1A278; the slots initialised by 0x02C1A0C4, +0xD9 1 as its init leaves it), with slot 0 held on (a game
    overlay there, priority 0x32 as the init leaves it): each frame the slot the draw takes (vt +0xAC, 0x02C1A288, run here)
    and its colour; with burns 0 (cleared by the arming) all along"""
    mod = e.alloc(0x100, b'\0')
    vt = e.alloc(0x100, b'\0')
    e.setw(mod, vt)
    e.setw(vt + 0x4C, CB_SET)
    e.setw(vt + C.COLOUR_CLEAR, CB_CLEAR)
    e.setw(vt + 0x8C, CB_PRIO)
    e.call(CB_INIT, mod)
    e.mu.mem_write(mod + 0xD9, b'\x01')
    pick = lambda: (e.call(CB_PICK, mod) - (mod + 8)) // 0x4C   # noqa: E731
    col = lambda sl: tuple(round(x, 4) for x in struct.unpack('>4f', bytes(e.mu.mem_read(mod + 0x4C * sl + 0x18, 16))))   # noqa: E731,E501
    e.call(CB_SET, mod, e.alloc(16, struct.pack('>4f', 1.0, 1.0, 1.0, 0.3)), 0, 0)   # a game overlay in slot 0
    old = e.w(vacc + C.W_COLOUR)
    e.setw(vacc + C.W_COLOUR, mod)
    before = (pick(), e.w(mod + 0x4C), e.w(mod + 0x98))
    put([(100, 15, 0.25, 2)])
    hit(4)
    rows = []
    for t in range(1, N + 1):
        frame()
        rows.append((pick(), col(1), e.mu.mem_read(mod + 0x9C, 1)[0], e.w(mod + 0x98), sum(1 for kk in range(C.BURN_CAP)
                                                                                   if e.w(A['btab'] + (4 * C.BURN_CAP + kk) * 16))))
    want = [(1, tuple(round(x, 4) for x in fl[t - 1]), 1, C.ICE_PRIO, 0) for t in range(1, N + 1)]
    check('ice2 (the user: "the opponent flashing doesn\'t occur"): the game\'s own ColorBlendModule code, slot 0 held on by '
          'a game overlay: before, the draw takes slot 0 (%s: the priorities equal, 0x32 / 0x32, so ice detonation v1\'s '
          'slot 1 colour, written every frame, was hidden whenever slot 0 was on); now every countdown frame 1 - %d the '
          'draw takes slot 1 (priority %d), its colour the flash\'s (yellow / black in turn), with no burns on the victim'
          % (before, N, C.ICE_PRIO), (before[0], [r for r in rows if r[0] != 1 or r[2] != 1][:3], rows == want,
                                      ''.join('Y' if r[1][0] > 0.5 else 'K' for r in rows) ==
                                      ''.join('Y' if c[0] > 0.5 else 'K' for c in fl)),
          (0, [], True, True))
    frame()
    check('ice2: the countdown over: slot 1 off, its priority back to 0x32, the draw back on slot 0 (the game\'s own colour: '
          'nothing stuck yellow or black)', (e.mu.mem_read(mod + 0x9C, 1)[0], e.w(mod + 0x98), pick()), (0, 0x32, 0))
    e.mu.mem_write(mod + 0x50, b'\x00')
    put([(100, 15, 0.25, 2)])
    hit(4)
    for _ in range(5):
        frame()
    mid = (pick(), col(1)[:3])
    e.call(lab['gk_clear'], until=C.CLEAR_BACK)
    frame()
    check('ice2: slot 0 off: the flash drawn too (frame 5, black: %s); a reset mid-countdown: slot 1 off, priority 0x32, '
          'nothing drawn from either slot' % (mid,), (mid[0], e.mu.mem_read(mod + 0x9C, 1)[0], e.w(mod + 0x98), st()[0]),
          (1, 0, 0x32, 0))
    e.setw(vacc + C.W_COLOUR, old)



def ccol_checks(patched, info, diag):
    """parabeetle v2 (feature ccol; the user: "Clones don't share the same costume as the original Greninja if an
    alternate palette was selected"): the weapon model set-up's call (CC_HOOK) through CC_TRAMP to cc_model: other kinds
    straight on; the clone's +8 (entry) / +0x4A (costume) from the Greninja making it (his TIMER_15) or the first live one,
    his entry's costume in the resource manager's table, before the game's model set-up (0x02B62F14) runs"""
    lab, A, F, img = info['labels'], info['A'], info['feats'], info['img']
    if 'ccol' not in F:
        check('ccol off: the model set-up\'s call is the game\'s (bl 0x%08X)' % C.CC_SETUP,
              K.branch_target(C.CC_HOOK, img.w(C.CC_HOOK)), C.CC_SETUP)
        return
    e = Run(patched)
    e.osr_full = []
    if diag:
        e.stub(C.OSREPORT_VENEER, lambda e_: e_.osr_full.append(tuple(e_.r(i) for i in range(3, 11))))
    check('ccol: the weapon model set-up call (0x%08X, in 0x02B63268 for kinds past 0x165) -> CC_TRAMP 0x%08X (lis / ori / '
          'mtctr / bctr) -> cc_model' % (C.CC_HOOK, C.CC_TRAMP),
          (K.branch_target(C.CC_HOOK, e.w(C.CC_HOOK)), e.w(C.CC_HOOK) & 1, [e.w(C.CC_TRAMP + 4 * i) for i in range(4)]),
          (C.CC_TRAMP, 1, [0x3D800000 | (lab['cc_model'] >> 16), 0x618C0000 | (lab['cc_model'] & 0xFFFF), 0x7D8903A6,
                           0x4E800420]))
    calls = []
    e.stub(C.CC_SETUP, lambda e_: calls.append((e_.r(3), e_.w(e_.r(3) + 8), e_.mu.mem_read(e_.r(3) + 0x4A, 1)[0])))
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    mgr = e.alloc(0x100, b'\0')
    e.setw(C.CC_RES_MGR, mgr)
    res = {}
    for ent, colour in ((0, 0), (1, 5), (2, 7), (3, 2), (4, 6)):
        r = e.alloc(0x40, b'\0')
        e.mu.mem_write(r + 0x28, struct.pack('>I', colour))
        e.setw(mgr + 0x58 + 4 * ent, r)
        res[ent] = colour

    def weapon(kind, ent=0x1234, col=0):
        w = e.alloc(0x100, b'\0')
        e.setw(w + 4, kind)
        e.setw(w + 8, ent)
        e.mu.mem_write(w + 0x4A, bytes([col]))
        return w

    def run(w):
        del calls[:]
        e.osr_full = []
        e.call(lab['cc_model'], w)
        return calls[0] if calls else None
    gk2 = e.fighter(2)
    e.mu.mem_write(gk2['f'] + 0x1E, b'\x04')
    e.setw(gk2['f'] + 8, 1)                         # his entry 1 (costume 5)
    w = weapon(C.PB_KIND, 0x1234, 3)
    check('ccol: another kind (the Parabeetle\'s): straight on to the game\'s set-up, untouched', run(w), (w, 0x1234, 3))
    e.vars = {}
    w = weapon(C.CLONE_KIND, 0x1234, 0)
    check('ccol: the clone, one live Greninja (player 3, entry 1, his costume c05), no TIMER_15: his (the first live '
          'Greninja\'s): +8 = 1, +0x4A = 5, then the game\'s set-up', run(w), (w, 1, 5))
    if diag:
        check('ccol diag: S4CK (owner player 3 (the table\'s 2), entry 1 (was 0x1234), costume 5 (was 0), found by 0 the '
              'first Greninja)', [x[1:7] for x in e.osr_full if x[0] == A['gk_fck']], [(3, 1, 0x1234, 5, 0, 0)])
    gk4 = e.fighter(4)
    e.mu.mem_write(gk4['f'] + 0x1E, b'\x04')
    e.setw(gk4['f'] + 8, 3)                         # entry 3 (costume c02)
    for whose, want in ((4, (3, 2)), (2, (1, 5))):
        e.vars = {C.CC_VAR: 3.0}
        # (the emulator's WorkModule stub answers every fighter the same: make the other one fail the read instead)
        other = gk2 if whose == 4 else gk4
        blk = e.w(other['f'] + C.ACC)
        saved = e.w(blk + C.WORK)
        e.setw(blk + C.WORK, 0)
        w = weapon(C.CLONE_KIND, 0, 0)
        got = run(w)
        e.setw(blk + C.WORK, saved)
        check('ccol: two Greninjas (players 3 / 5, costumes c05 / c02), the one making it (his TIMER_15 set: the table\'s %d): '
              'his entry %d and costume c%02d' % (whose, want[0], want[1]), got[1:], want)
    e.vars = {}
    w = weapon(C.CLONE_KIND, 0, 0)
    check('ccol: two Greninjas, no TIMER_15 set: the first live one (player 3, c05)', run(w)[1:], (1, 5))
    e.setw(gk2['f'] + 8, 9)                         # (not an entry: his player slot - 1 = 1)
    w = weapon(C.CLONE_KIND, 0, 0)
    check('ccol: his +8 not an entry (9): his player slot - 1 (the table\'s index 2: player 3 -> entry 2, c07)', run(w)[1:],
          (2, 7))
    e.setw(gk2['f'] + 8, 1)
    e.setw(mgr + 0x58 + 4 * 1, 0)
    w = weapon(C.CLONE_KIND, 0x22, 4)
    check('ccol: his entry has no resource record: left as it was (the game\'s own pick)', run(w)[1:], (0x22, 4))
    e.setw(C.CC_RES_MGR, 0)
    w = weapon(C.CLONE_KIND, 0x22, 4)
    check('ccol: no resource manager: left as it was', run(w)[1:], (0x22, 4))
    for f in (gk2, gk4):
        e.mu.mem_write(f['f'] + 0x1E, b'\x00')
    e.setw(C.CC_RES_MGR, mgr)
    w = weapon(C.CLONE_KIND, 0x22, 4)
    check('ccol: no live Greninja: left as it was', run(w)[1:], (0x22, 4))
    # the game's own decode (0x02B63268's) of +8 into +0x4A, for the record: entry e -> the entry's costume
    check('ccol: the game\'s weapon set-up reads +8 (its 0x02B632B0 lwz 8(r30)), decodes the entry into +0x4A from the '
          'resource manager\'s [+0x58 + 4 entry] +0x2B (0x02B63330 - 0x02B63344) and calls the model set-up at 0x%08X'
          % C.CC_HOOK, (img.w(0x02B632B0), img.w(0x02B63330), img.w(0x02B63340), img.w(0x02B63344)),
          (0x83FE0008, 0x809E0008, 0x88030028 + 3, 0x981E004A))


def fx3_entries(e, vacc):
    """ice3: the victim's Outline_Set entry (ol_tab: phase, w, rim rgb, rgb, tint, weight) and Outline_Shell entry (os_tab:
    phase, rgb, alpha, width, weight), each (index, values) or None; the two tables' counts"""
    def find(tab, n, ent):
        for i in range(n):
            if e.w(tab + ent * i) == vacc:
                return i, tab + ent * i
        return None, None
    i, a = find(C.OL_TAB, C.OL_N, C.OL_ENT)
    rf = lambda x, n: tuple(round(v, 4) for v in struct.unpack('>%df' % n, bytes(e.mu.mem_read(x, 4 * n))))   # noqa: E731
    ol = (i, e.w(a + 4), e.w(a + 8), rf(a + 0xC, 1), rf(a + 0x1C, 3), rf(a + 0x28, 3), rf(a + 0x34, 1), rf(a + 0x40, 1)) if a \
        else None
    j, b = find(C.OS_TAB, C.OS_N, C.OS_ENT)
    os_ = (j, e.w(b + 4), e.w(b + 8), rf(b + 0x1C, 3), rf(b + 0x28, 1), rf(b + 0x2C, 1), rf(b + 0x40, 1)) if b else None
    return ol, os_, e.w(C.OL_TAB - 0x20), e.w(0x04BE5D10)


def fx3_countdown_checks(e, A, N, fl, seen, ents, vmi, diag, ifl=()):
    """ice3 (parabeetle v2; the user's log: slot 1 on, priority 1000, nothing seen): each countdown frame the victim's
    Outline_Set entry (the body tint: FB1 blinkColor at its model's draw) and Outline_Shell entry (the band) hold the flash's
    colour; the outline cave's own FB1 write (0x04BE3674, the base exe's code, run here) then makes blinkColor the flash"""
    r4 = lambda c: tuple(round(x, 4) for x in c)   # noqa: E731
    want_ol = [(0, vmi, 2, (1.0,), r4(tuple(x * C.ICE3_RIM for x in c[:3])), r4(c[:3]), (round(c[3], 4),), (1.0,))
               for c in fl]
    got_ol = [x[0] for x in ents[:N]]
    check('ice3: frames 1 - %d the victim\'s Outline_Set entry (table 0x%08X, entry 0: free before): its model instance, held '
          '(phase 2, w 1, weight 1), the colour (rim x %g at its edges), the tint = the flash\'s alpha (0.35 / 0.6 / 0.8): '
          'yellow / black in turn' % (N, C.OL_TAB, C.ICE3_RIM), [i for i, (g_, w_) in enumerate(zip(got_ol, want_ol)) if g_ != w_][:3],
          [])
    want_os = [(0, vmi, 2, r4(c[:3]), (round(c[3] * C.ICE3_SHELL_ALPHA, 4),), (C.ICE3_SHELL_W,), (1.0,)) for c in fl]
    got_os = [x[1] for x in ents[:N]]
    check('ice3: ... and its Outline_Shell entry (table 0x%08X: the band round it, as the burn tint\'s outline that shows in '
          'game): the colour, alpha x %g, width %g px, held' % (C.OS_TAB, C.ICE3_SHELL_ALPHA, C.ICE3_SHELL_W),
          [i for i, (g_, w_) in enumerate(zip(got_os, want_os)) if g_ != w_][:3], [])
    check('ice3: the tables\' counts kept by their own count routines (ol_count / os_count: 1 entry in use each)',
          sorted({x[2:] for x in ents[:N]}), [(1, 1)])
    check('ice3: frame %d (the blast out): both entries let go (free, counts 0), %d nothing' % (N + 1, N + 2),
          [x[:2] for x in ents[N:]] + [x[2:] for x in ents[N:]], [(None, None)] * 2 + [(0, 0)] * 2)
    # the outline cave's FB1 write on a model instance's buffer, with the entry of frame 1 / 4 (yellow / black at 0.8)
    for t in (4, 7):
        c = fl[t - 1]
        ol = ents[t - 1][0]
        a = C.OL_TAB
        e.setw(a, 0x7FFF0000)                         # (any accessor: the write matches by model instance)
        e.setw(a + 4, vmi)
        e.setw(a + 8, 2)
        e.mu.mem_write(a + 0xC, struct.pack('>f', 1.0))
        e.mu.mem_write(a + 0x1C, struct.pack('>3f', *ol[4]))
        e.mu.mem_write(a + 0x28, struct.pack('>3f', *ol[5]))
        e.mu.mem_write(a + 0x34, struct.pack('>f', ol[6][0]))
        e.mu.mem_write(a + 0x40, struct.pack('>f', 1.0))
        e.setw(C.OL_TAB - 0x20, 1)
        fb = e.alloc(0x2A0, b'\0')
        e.mu.mem_write(fb + 0x40, struct.pack('>4f', 0.3, 0.3, 0.3, 0.0))   # the game's own blink: none (alpha 0)
        e.call(0x04BE3674, 0, vmi, fb)
        blink = tuple(round(x, 3) for x in struct.unpack('>4f', bytes(e.mu.mem_read(fb + 0x40, 16))))
        rim = tuple(round(x, 3) for x in struct.unpack('>3f', bytes(e.mu.mem_read(fb + 0x1D0, 12))))
        check('ice3: the outline cave\'s own FB1 write (0x04BE3674, the base exe\'s) with frame %d\'s entry: the model\'s '
              'blinkColor = the flash (%s at alpha %.2f: the shader draws lit x (1 - a) + rgb x a), its edges + the colour'
              % (t, 'yellow' if c[0] > 0.5 else 'black', c[3]), (blink, rim),
              (tuple(round(x, 3) for x in c[:3]) + (round(c[3], 3),), tuple(round(x * C.ICE3_RIM, 3) for x in c[:3])))
        e.setw(a, 0)
        e.setw(a + 8, 0)
        e.setw(C.OL_TAB - 0x20, 0)
    if diag:
        lines = list(ifl)
        f32 = lambda v: struct.unpack('>f', struct.pack('>f', v))[0]   # noqa: E731
        x100 = lambda v: int(f32(f32(v) * 100.0))                        # noqa: E731  (fmuls, fctiwz)
        check('ice3 diag: S4IF every 8th frame with every channel x100 (r, g, b, alpha) and the entries (body tint x 100 + '
              'band: 0)', [tuple(x[1:8]) for x in lines][:3],
              [(4, t, x100(fl[t - 1][0]), x100(fl[t - 1][1]), x100(fl[t - 1][2]), x100(fl[t - 1][3]), 0) for t in (1, 9, 17)])


def fx3_end_checks(e, A, put, hit, frame, vacc, vst):
    """ice3: a KO or a reset mid-countdown lets both entries go (the victim's own colour back); an entry a command took over
    (another accessor) is left alone"""
    put([(100, 15, 0.25, 2)])
    hit(4)
    for _ in range(5):
        frame()
    mid = fx3_entries(e, vacc)
    e.setw(vst + C.ST_KIND, C.ST_DEAD)
    frame()
    ko = fx3_entries(e, vacc)
    e.setw(vst + C.ST_KIND, 0)
    check('ice3: mid-countdown both entries on; the victim KO\'d: both let go at once', (mid[0] is not None,
                                                                                       mid[1] is not None, ko), (True, True, (None, None, 0, 0)))
    put([(100, 15, 0.25, 2)])
    hit(4)
    for _ in range(3):
        frame()
    a = C.OL_TAB
    rec0 = e.w(A['ice_fx'] + 16 * 4)
    e.setw(a, 0x7EEE0000)                             # an Outline_Set command took its entry over (another object's)
    frame()
    rec1 = e.w(A['ice_fx'] + 16 * 4)
    e.setw(vst + C.ST_KIND, C.ST_DEAD)
    frame()
    e.setw(vst + C.ST_KIND, 0)
    check('ice3: its entry taken over by a command (another accessor): the flash takes a free one the next frame, and its '
          'end lets go only its own (the command\'s left alone)', (rec0 == a, rec1 == a + C.OL_ENT, e.w(a), e.w(a + C.OL_ENT)),
          (True, True, 0x7EEE0000, 0))
    e.setw(a, 0)
    e.setw(a + 8, 0)


def ice_checks(e, info, diag):
    """ice detonation v1 (feature ice): the victim hit handler's hook (ICE_HOOK -> ice_hit, back at ICE_BACK with the game's
    word done), the trigger (an ice hit on a burning fighter: its burns cleared, recorded, armed; not ice / not burning /
    armed: nothing), burns refused while armed, the countdown (the flash in the tint's slot every frame, the blast asked
    of a Greninja at frame 51 with the request's values, the colour off at 53), the owner / fallback / none, a KO and a
    reset cancelling it, tr_claim taking the blast's request first with no burn context"""
    from unicorn.ppc_const import UC_PPC_REG_FPR1 as F1
    lab, A, F = info['labels'], info['A'], info['feats']
    if 'ice' not in F:
        check('ice off: the victim hit handler\'s word is the game\'s', '%08X' % e.w(C.ICE_HOOK), '%08X' % C.ICE_ORIG)
        return
    snd = 'ice2' in F
    fx3 = 'ice3' in F                                   # parabeetle v2: the flash through the outline caves
    IV, SV = C.ice_vars(F)                              # (ice3: the request in New_Var 60 - 63, the sound TIMER_13 / 14)
    SNDV = C.ICE3_SND_VALUE if fx3 else 1.0
    N = C.ice_frames(F)                                 # ice2: 156 (the user: "please triple the delay"), v1 52
    P_ = [('prio', C.ICE_PRIO, C.BTINT_SLOT)] if snd and not fx3 else []   # ice2: the slot's priority raised each frame
    P0 = [('prio', 0x32, C.BTINT_SLOT)] if snd and not fx3 else []        # ... and put back when it ends
    check('ice2 %s: ice_snd %s' % ('on' if snd else 'off', 'in the cave' if snd else 'not built'), 'ice_snd' in lab, snd)
    SP, SS = SV, SV + 1

    def sndv():                                         # (play, stop) written, the victim's +0x1C (its sound's Greninja)
        return (e.vars.get(SP), e.vars.get(SS), e.w(A['ice_st'] + C.ICE_ST * 4 + 0x1C))
    check('ice: the victim hit handler (0x%08X, lwz r3, 0x20(r27)) -> b ice_hit' % C.ICE_HOOK,
          K.branch_target(C.ICE_HOOK, e.w(C.ICE_HOOK)), lab['ice_hit'])
    fl = C.ice_flash(N)
    check('ice: the flash table: %d frames, yellow / black in turn, 3 frames each to %d then 2, fading in over frames 1 - 2'
          % (N, 90 if snd else 30), (len(fl), [round(c[3], 2) for c in fl[:3]],
                                     ''.join('Y' if c[0] > 0.5 else 'K' for c in fl)),
          (N, [0.35, 0.6, 0.8], 'YYYKKK' * (15 if snd else 5) + 'YYKK' * (16 if snd else 5) + 'YY'))
    rd = lambda a, n: [round(x, 4) for x in struct.unpack('>%df' % n, bytes(e.mu.mem_read(a, 4 * n)))]   # noqa: E731
    check('ice: the flash table in the cave', [tuple(rd(A['ice_flash'] + 16 * i, 4)) for i in range(N)],
          [tuple(round(x, 4) for x in c) for c in fl])
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    for kk in range(C.SLOTS * C.BURN_CAP):
        e.setw(A['btab'] + 16 * kk, 0)
    for i in range(C.SLOTS * C.ICE_ST // 4):
        e.setw(A['ice_st'] + 4 * i, 0)
    for i in range(C.SLOTS * 4):
        e.setw(A['bti_st'] + 4 * i, 0)
    for i in range(C.SLOTS):
        e.setw(A['bfx_lvl'] + 4 * i, 0)
    gk = e.fighter(2, x=-20.0)
    e.mu.mem_write(gk['f'] + 0x1E, b'\x04')
    gacc = e.w(gk['f'] + C.BASE_ACC)
    gst = e.alloc(0x60, b'\0')
    e.setw(gacc + C.F_STATUS, gst)
    vic = e.fighter(4)
    e.mu.mem_write(vic['f'] + 0x1E, b'\x04')
    e.setw(vic['f'] + 4, 0x3)                           # Mario
    vacc = e.w(vic['f'] + C.BASE_ACC)
    vpost = e.alloc(0x40, b'\0')
    e.mu.mem_write(vpost + 0x10, struct.pack('>2f', 30.0, 12.0))
    e.setw(vacc + C.W_POSTURE, vpost)
    vst = e.alloc(0x60, b'\0')
    e.setw(vacc + C.F_STATUS, vst)
    vmm = e.alloc(0x20, b'\0')                          # ice3: its ModelModule -> its model instance (the outlines')
    vmi = e.alloc(0x40, b'\0')
    e.setw(vacc + 0x3C, vmm)
    e.setw(vmm + 0xC, vmi)
    cvt = e.alloc(0x100, b'\0')
    cset, cclr, cpri = e.alloc(4), e.alloc(4), e.alloc(4)
    e.setw(cvt + 0x4C, cset)
    e.setw(cvt + C.COLOUR_CLEAR, cclr)
    e.setw(cvt + 0x8C, cpri)
    cbm = e.alloc(0x100, b'\0')
    e.setw(cbm, cvt)
    e.setw(vacc + C.W_COLOUR, cbm)
    calls = []
    e.stub(cset, lambda e_: calls.append(('set', tuple(rd(e_.r(4), 4)), e_.r(5), e_.r(6))))
    e.stub(cclr, lambda e_: calls.append(('clear', e_.r(4))))
    e.stub(cpri, lambda e_: calls.append(('prio', e_.r(4), e_.r(5))))
    # the attacker objects (the battle object manager's records)
    mgr = e.alloc(0x40, b'\0')
    e.setw(C.SH_MANAGER, mgr)
    recs = {}
    e.stub(C.SH_LOOKUP, lambda e_: recs.get(e_.r(4), 0))

    def attacker(oid, x):
        acc = e.alloc(0x100, b'\0')
        post = e.alloc(0x40, b'\0')
        e.mu.mem_write(post + 0x10, struct.pack('>f', x))
        e.setw(acc + C.W_POSTURE, post)
        rec = e.alloc(0x40, b'\0')
        e.setw(rec + 0xC, acc)
        e.mu.mem_write(rec + 0x1E, b'\x04')
        recs[oid] = rec
    attacker(0x00010000, 10.0)                          # left of the victim (x 30)
    attacker(0x10002000, 50.0)                          # right of it (a projectile)
    info_ = e.alloc(0xE4, b'\0')

    def hit(element, att=0x00010000, acc=None):
        e.mu.mem_write(info_ + C.HIT_ELEMENT, bytes([element]))
        e.setw(info_ + C.HIT_ATTACKER, att)
        for i in range(14, 32):
            e.mu.reg_write(REGS[i], 0x5A5A0000 + i)
        e.mu.reg_write(REGS[27], acc or vacc)
        e.mu.reg_write(REGS[28], info_)
        e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        e.osr_full = []
        e.call(C.ICE_HOOK, until=C.ICE_BACK)
        return (e.r(3) == e.w((acc or vacc) + 0x20) and e.r(27) == (acc or vacc) and e.r(28) == info_ and
                all(e.r(i) == 0x5A5A0000 + i for i in range(14, 27) if i not in (27, 28)) and
                e.mu.reg_read(UC_PPC_REG_1) == 0x70000000 + 0xF0000)

    def put(ins, v=4):
        for kk in range(C.BURN_CAP):
            a = A['btab'] + (v * C.BURN_CAP + kk) * 16
            if kk < len(ins):
                f_, iv, dmg, ow = ins[kk]
                e.setw(a, f_)
                e.setw(a + 4, (iv << 16) | iv)
                e.setw(a + 8, ow)
                e.mu.mem_write(a + 12, struct.pack('>f', dmg))
            else:
                e.setw(a, 0)

    def insts(v=4):
        return sum(1 for kk in range(C.BURN_CAP) if e.w(A['btab'] + (v * C.BURN_CAP + kk) * 16))

    def st(v=4):
        a = A['ice_st'] + C.ICE_ST * v
        sw = lambda o: struct.unpack('>i', struct.pack('>I', e.w(a + o)))[0]   # noqa: E731
        return (sw(0), rd(a + 4, 1)[0], sw(8), sw(0xC), rd(a + 0x10, 1)[0], rd(a + 0x14, 1)[0], sw(0x18))

    def frame():
        del calls[:]
        e.osr_full = []
        e.call(lab['burn_him'], gk['f'], 2)
        return list(calls)
    rows = {m[0]: m for m in C.BURN_MOVES}
    sm, nair = rows[95], rows[104]
    burns = [(160, sm[2], sm[1], 2), (100, nair[2], nair[1], 2), (200, sm[2], sm[1], 5), (30, 6, 0.6, 2)]
    ref = C.ice_amount(burns)
    # not ice / not burning
    put(burns)
    kept = hit(2)
    check('ice: a slash (Effect 2) hit on a burning fighter: nothing (its 4 burns kept, not armed); back at 0x%08X with the '
          'game\'s word (r3 its StatusModule) and the caller\'s registers' % C.ICE_BACK, (kept, insts(), st()[0]), (True, 4, 0))
    put([])
    check('ice: an ice (Effect 4) hit on a fighter not burning: nothing armed', (hit(4), st()[0]), (True, 0))
    check('ice: an ice hit on an object that is no fighter (an accessor not in the table): nothing',
          hit(4, acc=e.alloc(0x100, b'\0')) or True, True)
    # the trigger
    put(burns)
    e.setw(A['bti_st'] + 16 * 4, 2)
    e.setw(A['bti_st'] + 16 * 4 + 4, C.BTINT_FADE)
    e.vars = {}
    hit(4)
    arm_snd = sndv()
    got = st()
    check('ice: an ice hit on a burning fighter (Mario, slot 4: two smash burns of his, a neutral air, a skeleton row of '
          'another Greninja (slot 5)): every burn cleared, armed (t 1); remaining %.3f %%, 4 stacks, owner slot 2 (the most), '
          'way +1 (the attacker left of it), b = %.3f (+ 0.5 a stack)' % (ref[0], ref[3]),
          (insts(), got[0], round(got[1], 2), got[2], got[3], got[4], round(got[5], 2), got[6]),
          (0, 1, round(ref[0], 2), 4, ref[2], 1.0, round(ref[3], 2), -1))
    check('ice: ... its burn tint off the next frame (bti_st tier 0, fade -1)',
          (e.w(A['bti_st'] + 16 * 4), struct.unpack('>i', struct.pack('>I', e.w(A['bti_st'] + 16 * 4 + 4)))[0]), (0, -1))
    if diag:
        check('ice diag: S4IA (victim 4, amount x100, 4 stacks, owner 2, way 1)',
              [x[1:6] for x in e.osr_full if x[0] == A['gk_fia']], [(4, int(ref[3] * 100), 4, 2, 1)])
    if snd:
        check('ice2: on the arming hit the detonation\'s sound asked of the owner (Greninja slot 2: his VAR 0x%08X = %g, '
              'played by his MSC), recorded at the victim\'s +0x1C (slot + 1 = 3); no stop' % (SP, SNDV), arm_snd, (SNDV, None, 3))
        if diag:
            check('ice2 diag: S4ID (victim 4, cmd 1 play, Greninja slot 2)',
                  [x[1:4] for x in e.osr_full if x[0] == A['gk_fid']], [(4, 1, 2)])
    else:
        check('ice2 off: the arming hit asks no sound', (arm_snd[0], arm_snd[1]), (None, None))
    put([(60, 6, 0.4, 2)])
    e.vars = {}
    hit(4)
    if snd:
        check('ice2: an ice re-hit while armed: no second sound (once an arming)', sndv(), (None, None, 3))
    check('ice: an ice re-hit while armed: ignored (the record kept, the new burn not cleared)', (st()[:3], insts()),
          (got[:3], 1))
    put([])
    # burns refused while armed
    node = e.alloc(0x30, b'\0')
    e.setw(node + C.NODE_OBJ, (4 << 16) | 0x11)
    e.mu.mem_write(node + C.NODE_TYPE, b'\x01')
    e.call(lab['burn_add'], node, A['bmoves'], 2)
    check('ice: a burn landing on an armed victim (burn_add): not taken', insts(), 0)
    # the countdown
    e.vars = {}
    seen, asked, ents, ifl = [], None, [], []
    if fx3:
        for tab, n, ent, cnt in ((C.OL_TAB, C.OL_N, C.OL_ENT, C.OL_TAB - 0x20), (C.OS_TAB, C.OS_N, C.OS_ENT, 0x04BE5D10)):
            e.mu.mem_write(tab, bytes(n * ent))        # (the outline tables as a match starts: the earlier checks' gone)
            e.setw(cnt, 0)
    for t in range(1, N + 3):
        got_ = frame()
        seen.append(got_)
        if fx3:
            ents.append(fx3_entries(e, vacc))
            if diag:
                ifl += [x for x in e.osr_full if x[0] == A['gk_fif']]
        if asked is None and any(k in e.vars for k in range(IV, IV + 4)):
            asked = t
    if snd:
        check('ice2: the countdown run out (the blast made): its sound neither played again nor stopped (the boom plays '
              'on), the record kept', sndv(), (None, None, 3))
    if fx3:
        fx3_countdown_checks(e, A, N, fl, seen, ents, vmi, diag, ifl)
    want_set = [P_ + [('set', tuple(round(x, 4) for x in fl[t - 1]), C.BTINT_SLOT, 0)] for t in range(1, N + 1)]
    check('ice: the countdown: frames 1 - %d the flash colour in the tint\'s slot %d (once a frame%s; the burn tint\'s reset '
          'clears it first on frame 1), frame %d the colour off%s, %d nothing' % (
              N, C.BTINT_SLOT, ', its priority raised to %d first' % C.ICE_PRIO if snd else '', N + 1,
              ' and its priority back to 0x32' if snd else '', N + 2),
          [seen[0][-1 - len(P_):]] + seen[1:N] + seen[N:],
          want_set + [[('clear', C.BTINT_SLOT)] + P0, []]) if not fx3 else \
        check('ice3: the countdown: frames 1 - %d no ColorBlendModule call of its own (slot 1 never drew: the user\'s log), '
              'only the burn tint\'s reset clear on frame 1; frame %d its slot cleared (no priority to put back: never '
              'changed), %d nothing' % (N, N + 1, N + 2), [seen[0][1:]] + seen[1:N] + seen[N:],
              [[]] * N + [[('clear', C.BTINT_SLOT)], []])
    t_ = 4 + ref[3] / 100.0
    check('ice: the blast asked at frame %d of Greninja slot 2 (the owner): his VAR 0x%08X - +3 = type 4 + b / 100 = %.4f, '
          'the victim\'s x 30, y 12 + %g, way +1; the state free again' % (N - C.ICE_LEAD, IV, t_, C.ICE_Y),
          (asked, [round(e.vars.get(IV + i, -99.0), 3) for i in range(4)], st()[0], st()[6]),
          (N - C.ICE_LEAD, [round(t_, 3), 30.0, round(12.0 + C.ICE_Y, 3), 1.0], 0, 2))
    # the way: an attacker right of it; the owner not there: another Greninja; none
    gk5 = e.fighter(5, x=0.0)
    e.mu.mem_write(gk5['f'] + 0x1E, b'\x04')
    e.vars = {}
    put([(100, 15, 0.25, 6)])                       # owner slot 6: not in the match
    hit(4, att=0x10002000)
    check('ice: an attacker right of the victim (a projectile at x 50): way -1; owner slot 6', (st()[4], st()[3]), (-1.0, 6))
    for _ in range(N):
        frame()
    check('ice: the owner gone: the first live Greninja (slot 2) asked', (st()[6], round(e.vars.get(IV + 3, 0), 3)),
          (2, -1.0))
    for _ in range(3):
        frame()
    e.setw(gst + C.ST_KIND, C.ST_DEAD)
    e.vars = {}
    put([(100, 15, 0.25, 2)])
    hit(4)
    for _ in range(N):
        frame()
    check('ice: the owner (slot 2) KO\'d (Dead): Greninja slot 5 asked', st()[6], 5)
    if snd:
        check('ice2: ... and its sound from him too (the blast\'s choice: +0x1C slot 5 + 1)', sndv(), (SNDV, None, 6))
    for _ in range(3):
        frame()
    e.mu.mem_write(gk5['f'] + 0x1E, b'\x00')
    e.vars = {}
    put([(100, 15, 0.25, 2)])
    hit(4)
    for _ in range(N):
        frame()
    check('ice: no Greninja who can: no blast asked (none of his VARs written), the Greninja asked -1',
          (sorted(k for k in e.vars if IV <= k < IV + 4), st()[6]), ([], -1))
    if snd:
        check('ice2: no Greninja who can: no sound played, none to stop (no blast: no boom)', sndv(), (None, None, 0))
    for _ in range(3):
        frame()
    e.setw(gst + C.ST_KIND, 0)
    # a KO cancels it
    e.vars = {}
    put([(100, 15, 0.25, 2)])
    hit(4)
    for _ in range(10):
        frame()
    e.setw(vst + C.ST_KIND, C.ST_DEAD)
    e.vars = {}
    got = frame()
    check('ice: the victim KO\'d (Dead) at frame 11: the colour off at once%s, the countdown over' % (
        ' (its priority back)' if snd else ''), (got[-1 - len(P0):], st()[0]), ([('clear', C.BTINT_SLOT)] + P0, 0))
    if snd:
        check('ice2: ... its sound stopped (Greninja slot 2: his VAR 0x%08X = %g, his MSC SoundModule 0x2714), the '
              'record cleared' % (SS, SNDV), sndv(), (None, SNDV, 0))
        if diag:
            check('ice2 diag: S4ID (victim 4, cmd 2 stop, Greninja slot 2)',
                  [x[1:4] for x in e.osr_full if x[0] == A['gk_fid']], [(4, 2, 2)])
    if diag:
        check('ice diag: S4IC (victim 4, status 0xB1, frame 11)', [x[1:4] for x in e.osr_full if x[0] == A['gk_fic']],
              [(4, C.ST_DEAD, 11)])
    for _ in range(N):
        frame()
    check('ice: ... and no blast asked afterwards', sorted(k for k in e.vars if IV <= k < IV + 4), [])
    if snd:
        check('ice2: ... nor any sound again', (e.vars.get(SP), e.vars.get(SS)), (None, SNDV))
    e.setw(vst + C.ST_KIND, 0)
    # a reset cancels it
    put([(100, 15, 0.25, 2)])
    hit(4)
    frame()
    e.call(lab['gk_clear'], until=C.CLEAR_BACK)
    check('ice: a match / training reset (gk_clear): the countdown -1 (off asked)', st()[0], -1)
    e.vars = {}
    got = frame()
    if snd:
        check('ice2: ... the next frame its sound stopped (his MSC\'s own reset stops it too)', sndv(), (None, SNDV, 0))
    check('ice: ... the next frame the colour off, free again (the burn tint\'s own reset clears the slot too: twice)',
          (got, st()[0]), ([('clear', C.BTINT_SLOT)] * 2 + P0, 0))
    check('ice: ... nothing after', frame(), [])
    if snd and not fx3:                                 # ice2 (the user: "the opponent flashing doesn't occur")
        render_checks(e, lab, A, N, fl, put, hit, frame, st, vacc)
    if fx3:
        fx3_end_checks(e, A, put, hit, frame, vacc, vst)
    # the claim: the blast's request first, no burn context
    svt = e.alloc(0x100, b'\0')
    g, s_ = e.alloc(4), e.alloc(4)
    e.setw(svt + 0x44, g)
    e.setw(svt + 0x4C, s_)
    sv = {}
    e.stub(g, lambda e_: e_.mu.reg_write(F1, f2d(sv.get(e_.r(4), 0.0))))
    e.stub(s_, lambda e_: sv.__setitem__(e_.r(4), round(d2f(e_.mu.reg_read(F1)), 3)))
    w = e.alloc(0x40, b'\0')
    acc = e.alloc(0x100, b'\0')
    wm = e.alloc(0x10, b'\0')
    e.setw(wm, svt)
    e.setw(acc + C.W_WORK, wm)
    e.setw(w + C.W_ACC, acc)
    V = C.GK_VAR_TR
    e.vars = {V: 1.0, V + 1: 5.0, V + 2: 0.0, V + 3: 1.0, IV: 4.25, IV + 1: 30.0, IV + 2: 21.0,
              IV + 3: -1.0}
    e.call(lab['tr_frame'], w)
    check('ice: tr_claim: a blast request and a trail request: the blast\'s first (type 4.25, x 30, y 21, way -1), no burn '
          'context (VAR_5 0), his blast request cleared, the trail\'s kept',
          ([sv.get(0x0F000300 + i, 0.0) for i in range(6)], e.vars.get(IV), e.vars.get(V)),
          ([3.0, 4.25, 30.0, 21.0, -1.0, 0.0], 0.0, 1.0))
    e.vars = {}
    put([])


def pb_checks(patched, info, diag):
    """parabeetle v1 (feature pbeetle): the Parabeetle's kind (tables, descriptor and its motions, singleton, row), its
    claim (his VAR_12), its collision (parabeetle.lvd through the hydrant's GroundModule route: made, moved, made again,
    removed) on a fresh emulator"""
    lab, A, F, img = info['labels'], info['A'], info['feats'], info['img']
    if 'pbeetle' not in F:
        check('parabeetle: without "pbeetle": no parabeetle code', 'pb_frame' in lab, False)
        return
    e = Run(patched)
    if diag:
        e.osr_full = []
        e.stub(C.OSREPORT_VENEER, lambda e_: (e_.rec('osr', 3, 4, 5, 6),
                                               e_.osr_full.append(tuple(e_.r(i) for i in range(3, 11))))[1])
    T = info['T']
    k = C.PB_KIND - W.OLD_N
    check('parabeetle tables: name / folder "parabeetle", owner "gekkouga"',
          [e.cstr(e.w(T[nm] + 4 * C.PB_KIND)) for nm in ('owner', 'name', 'folder')], ['gekkouga', 'parabeetle', 'parabeetle'])
    check('parabeetle tables: base kind Mario\'s pump (the skeleton\'s), its own singleton / row',
          (e.w(T['bt'] + 4 * k), e.w(T['st'] + 4 * k), e.w(T['rt'] + 4 * k) + W.MODULE_TABLE & 0xFFFFFFFF),
          (C.ATTACK_BASE, A['pb_single'], A['pb_row']))
    u16 = e.mu.mem_read(T['u16'] + 2 * C.PB_KIND, 2)
    bun = img.h(W.STATIC_TABLES[2][1] + 2 * C.CLONE_BASE)
    check('parabeetle tables: u16 flags bunshin\'s without the Final Smash categories and the owner\'s colour (loaded with '
          'him, c00 only)', struct.unpack('>H', bytes(u16))[0], bun & ~(C.CATEGORY_BITS | 0x10))
    row = [e.w(A['pb_row'] + 4 * j) for j in range(28)]
    check('parabeetle row: the skeleton\'s (slot 5 the hydrant\'s GroundModule: grounds from an .lvd; slot 11 a '
          'SoundModule)', (row, row[5], row[C.SND_SLOT]), ([e.w(A['sk_row'] + 4 * j) for j in range(28)], C.SK_GM_CTOR,
                                                            C.SND_CTOR))
    e.call(e.w(T['dt'] + 4 * k))
    d = e.r(3)
    mi = e.w(d + 8)
    bd = W.descriptor_of(img, C.CLONE_BASE)
    check('parabeetle descriptor: a bunshin copy, 3 motions: anim_hash of FitGekkougaParabeetleMainA00Wait / A01Rise / '
          'A02Ridden (its main.pac)', (d, e.w(d + 0x1C), e.w(mi + 4), [e.w(e.w(mi) + 8 * i) for i in range(3)]),
          (A['pb_desc'], img.w(bd + 0x1C), 3, C.pb_hashes()))
    import mtable
    check('parabeetle motion hashes = tools/mtable.py anim_hash (the pack loader\'s key)',
          C.pb_hashes(), [mtable.anim_hash(n) for n in C.PB_MOTIONS])
    vt = A['pb_vt']
    check('parabeetle singleton: +0x34 sk_start (a last life\'s grounds removed, VARs 0), +0x94 pb_94, +0xAC sk_hit, the '
          'rest the moon\'s', (e.w(A['pb_single']), e.w(vt + 0x34), e.w(vt + 0x94), e.w(vt + W.HIT_METHOD)),
          (vt, lab['sk_start'], lab['pb_94'], lab['sk_hit']))
    lst = e.w(A['gk_desc'] + 8)
    check('his article list: 11 entries, article 10 the Parabeetle (0x1A4, 3 at once: his and his two clones\')',
          (e.w(lst + 4), [e.w(e.w(lst) + 16 * C.PB_ARTICLE + 4 * j) for j in range(4)]),
          (11, [C.PB_KIND, C.PB_MAX, 0, 0]))
    check('parabeetle strings: "parabeetle", "parabeetle.lvd"; its 2 vertices (x -10 / +10, y + 10.6: left to right)',
          (e.cstr(A['pb_str']), e.cstr(A['pb_lvd']),
           [round(x, 3) for x in struct.unpack('>4f', bytes(e.mu.mem_read(A['pb_verts'], 16)))]),
          ('parabeetle', 'parabeetle.lvd', [-10.0, 10.6, 10.0, 10.6]))
    # ---- the game's side, stubbed
    calls = []
    st = dict(file=1, ground=1)
    mgr = e.alloc(0x40, b'\0')
    e.setw(C.RES_MGR, mgr)
    e.setw(mgr + 0x30, 0xABC0)
    gm = e.alloc(0x200, b'\0')
    e.setw(gm, C.SK_GM_VT)
    ground = e.alloc(0x200, b'\0')
    gobj = e.alloc(0x100, b'\0')
    e.setw(ground, gobj)
    e.setw(gobj + 0x34, 2)

    def res_get(e_):
        calls.append(('res_get', e_.r(3), e_.r(5), e_.r(6), e_.r(7)))
        e_.setw(e_.r(4), 0x1111)

    def res_find(e_):
        calls.append(('res_find', e_.w(e_.r(3)), e_.cstr(e_.r(5)), e_.r(6)))
        e_.setw(e_.r(4), 0x2222 if st['file'] else 0)

    def gc_make(e_):
        calls.append(('make', e_.r(3), e_.r(4), e_.r(5), e_.r(6)))
        if st['ground']:
            e_.setw(e_.r(3) + 0xF0, ground)

    def vert(name):
        def f(e_):
            xy = bytes(e_.mu.mem_read(e_.r(5), 8))
            calls.append((name, e_.r(3), e_.r(4)) + tuple(round(x, 3) for x in struct.unpack('>2f', xy)))
        return f

    def gc_free(e_):
        calls.append(('col_free', e_.r(3)))
        e_.setw(e_.r(3) + 0xF0, 0)
    e.stub(C.RES_GET, res_get)
    e.stub(C.RES_FIND, res_find)
    e.stub(C.RES_ASSIGN, lambda e_: calls.append(('assign', e_.r(3), e_.w(e_.r(4)))))
    e.stub(C.RES_FREE, lambda e_: calls.append(('res_free', e_.r(4))))
    e.stub(C.GC_MAKE, gc_make)
    e.stub(C.GC_ON, lambda e_: calls.append(('on', e_.r(3), e_.r(4))))
    e.stub(C.GC_ENABLE, lambda e_: calls.append(('enable', e_.r(3))))
    e.stub(C.GC_SETV, vert('setv'))
    e.stub(C.GC_MOVEV, vert('movev'))
    e.stub(C.GC_COMMIT, lambda e_: calls.append(('commit', e_.r(3))))
    e.stub(C.GC_FREE, gc_free)
    e.stub(C.GC_FRAME, lambda e_: calls.append(('gmframe', e_.r(3))))
    # the beetle: its WorkModule (sv), place (30, 40), its GroundModule
    sv = {}
    svt = e.alloc(0x100, b'\0')
    g, s_ = e.alloc(4), e.alloc(4)
    e.setw(svt + 0x44, g)
    e.setw(svt + 0x4C, s_)
    e.stub(g, lambda e_: e_.mu.reg_write(UC_PPC_REG_FPR1, f2d(sv.get(e_.r(4), 0.0))))

    def sset(e_):
        sv[e_.r(4)] = round(d2f(e_.mu.reg_read(UC_PPC_REG_FPR1)), 3)
    e.stub(s_, sset)
    swm = e.alloc(0x10, b'\0')
    e.setw(swm, svt)
    bacc = e.alloc(0x100, b'\0')
    e.setw(bacc + C.W_WORK, swm)
    post = e.alloc(0x80, b'\0')
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 30.0, 40.0))
    e.setw(bacc + C.W_POSTURE, post)
    e.setw(bacc + 0x2C, gm)
    weapon = e.alloc(0x40, b'\0')
    e.setw(weapon + C.W_ACC, bacc)
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')

    def frame():
        del calls[:]
        e.calls, e.osr_full = [], []
        e.call(lab['pb_frame'], weapon)
        return list(calls)

    def logs(fmt):
        return [x[1:6] for x in e.osr_full if x[0] == A[fmt]] if diag else []

    # its start (the skeleton's +0x34)
    sv.update({0x0F000300 + v: 9.0 for v in range(13)})
    del calls[:]
    e.call(lab['sk_start'], 0, weapon, 0)
    check('parabeetle start (+0x34, the skeleton\'s): a last life\'s grounds removed, VARs 0-12 = 0',
          (calls, [sv[0x0F000300 + v] for v in range(13)]), ([('col_free', gm)], [0.0] * 13))
    # no request: nothing claimed
    me = e.fighter(2)
    e.mu.mem_write(me['f'] + 0x1E, b'\x04')
    e.vars = {}
    check('parabeetle: no request (his VAR_12 0): not claimed, nothing made', (frame(), sv[C.PB_VAR_SLOT]), ([], 0.0))
    # slot 2 a Mario with VAR_12 set (shared test variables): skipped; slot 3 him
    other = e.fighter(1)
    e.setw(other['f'] + 4, 0x1)
    e.mu.mem_write(other['f'] + 0x1E, b'\x04')
    e.vars = {C.GK_VAR_PBREQ: -5.0}
    c0 = frame()
    check('parabeetle claim: its owner the Greninja that asked (slot 3; slot 2 is no Greninja): VAR_0 3, VAR_1 his code '
          '-5 (facing left, his own, on the ground); his VAR_12 cleared',
          ([sv[C.PB_VAR_SLOT], sv[C.PB_VAR_CODE]], e.vars[C.GK_VAR_PBREQ]), ([3.0, -5.0], 0.0))
    check('parabeetle claim: phase 0 (its MSC not started): no collision yet', c0, [])
    if diag:
        check('parabeetle diag: S4PB (slot 3, code -5)', [x[:2] for x in logs('gk_fpb')], [(3, 0xFFFFFFFB)])
    e.vars = {C.GK_VAR_PBREQ: 2.0}
    frame()
    check('parabeetle: claimed once: a later request is left for the next beetle', e.vars[C.GK_VAR_PBREQ], 2.0)
    e.vars = {}
    # flying: the line made from parabeetle.lvd and placed at it
    sv[C.PB_VAR_PHASE] = 1.0
    c1 = frame()
    want_v = [(gm, i, 30.0 + vx, round(40.0 + vy, 3)) for i, (vx, vy) in enumerate(C.PB_VERTS)]
    check('parabeetle collision: as the skeleton\'s (the hydrant\'s set-up): its kind\'s bundle (kind 0x1A4), '
          '"parabeetle.lvd" in it, GroundModule +0xEC = the file, the grounds made (gm, 1, 0, 0), its 2 vertices placed at '
          'it (x +- 10, y + 10.6), the line recomputed, on (then the grounds turned on), both handles released',
          c1, [('res_get', 0xABC0, C.PB_KIND, 0, 0), ('res_find', 0x1111, 'parabeetle.lvd', 1), ('assign', gm + 0xEC, 0x2222),
               ('make', gm, 1, 0, 0)] + [('setv',) + v for v in want_v] +
              [('commit', gm), ('on', gm, 1), ('enable', gm), ('res_free', 2), ('res_free', 2)])
    check('parabeetle collision: VAR_6 = 1 (made)', sv[C.PB_VAR_COL], 1.0)
    if diag:
        check('parabeetle diag: S4PC state 1, its ground', [x[:2] for x in logs('gk_fpc')], [(1, ground)])
    # moved (forward 0.75, up 0.4): the vertices moved (riders carried), the GroundModule's frame update first
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 30.75, 40.4))
    c2 = frame()
    check('parabeetle collision: it moved (0.75, 0.4): its GroundModule\'s frame update, then its 2 vertices moved (the '
          'move call: last = where they were, so riders are carried), the line recomputed, kept on; no new set-up',
          c2, [('gmframe', gm)] + [('movev', gm, i, round(30.75 + vx, 3), round(40.4 + vy, 3))
                                   for i, (vx, vy) in enumerate(C.PB_VERTS)] + [('commit', gm), ('enable', gm)])
    for n in range(5):
        frame()
    check('parabeetle collision: every flying frame the same (5 more frames: 5 updates, 10 moves, no set-up)',
          sum(1 for c in calls if c[0] == 'movev'), 2)
    # a 4-vertex ground (another .lvd): not ours to move
    e.setw(gobj + 0x34, 4)
    check('parabeetle: a ground that isn\'t the 2-vertex line: nothing moved (made again: VAR_6 0, VAR_7 1)',
          ([c for c in frame() if c[0] in ('movev', 'setv')], sv[C.PB_VAR_COL], sv[C.PB_VAR_REMADE]), ([], 0.0, 1.0))
    e.setw(gobj + 0x34, 2)
    check('parabeetle: ... made again the next frame', [c[0] for c in frame()][:4], ['res_get', 'res_find', 'assign', 'make'])
    # its ground gone (id -1)
    e.setw(ground + 0x160, 0xFFFF0000)
    check('parabeetle: its ground gone (id -1): nothing moved, made again next frame (VAR_7 2)',
          (frame(), sv[C.PB_VAR_COL], sv[C.PB_VAR_REMADE]), ([], 0.0, 2.0))
    e.setw(ground + 0x160, 0)
    frame()
    e.setw(ground + 0x160, 0xFFFF0000)
    frame()
    e.setw(ground + 0x160, 0)
    frame()
    check('parabeetle: made again a 3rd time (VAR_7 3)', (sv[C.PB_VAR_COL], sv[C.PB_VAR_REMADE]), (1.0, 3.0))
    e.setw(ground + 0x160, 0xFFFF0000)
    frame()
    check('parabeetle: gone a 4th time: lost (VAR_6 4: not made again)', (sv[C.PB_VAR_COL], [c[0] for c in frame()]),
          (4.0, []))
    e.setw(ground + 0x160, 0)
    sv.update({C.PB_VAR_COL: 0.0, C.PB_VAR_REMADE: 0.0})
    e.setw(ground + 0x160, 0xFFFF0000)
    check('parabeetle: made but its line can\'t be placed (its ground gone at once): failed (VAR_6 3), not retried',
          ([c[0] for c in frame()], sv[C.PB_VAR_COL], [c[0] for c in frame()]),
          (['res_get', 'res_find', 'assign', 'make', 'res_free', 'res_free'], 3.0, []))
    e.setw(ground + 0x160, 0)
    sv.update({C.PB_VAR_COL: 1.0, C.PB_VAR_REMADE: 0.0})
    frame()
    # leaving: removed
    sv[C.PB_VAR_PHASE] = 2.0
    check('parabeetle leaving (its MSC\'s phase 2): the line removed (GC_FREE: anyone on it falls), VAR_6 2',
          (frame(), sv[C.PB_VAR_COL]), ([('col_free', gm)], 2.0))
    if diag:
        check('parabeetle diag: S4PF (slot 3)', [x[:1] for x in logs('gk_fpf')], [(3,)])
    check('parabeetle leaving: nothing more', frame(), [])
    # a missing lvd: failed, no grounds made
    sv.update({C.PB_VAR_PHASE: 1.0, C.PB_VAR_COL: 0.0})
    st['file'] = 0
    c3 = frame()
    check('parabeetle: no parabeetle.lvd in its files: failed (VAR_6 3), no grounds made, the handles released',
          ([c[0] for c in c3], sv[C.PB_VAR_COL]), (['res_get', 'res_find', 'res_free', 'res_free'], 3.0))
    st['file'] = 1
    # a GroundModule that isn't the hydrant's class: nothing
    sv.update({C.PB_VAR_COL: 0.0})
    e.setw(gm, 0x10001234)
    check('parabeetle: a GroundModule that isn\'t the hydrant\'s class: failed (VAR_6 3), no call',
          (frame(), sv[C.PB_VAR_COL]), ([], 3.0))
    e.setw(gm, C.SK_GM_VT)


def col_on_checks(patched):
    """skeleton v1.2: the game's own GC_ON / GC_ENABLE (0x02AC2EF0 / 0x02AC2E54) and the ground's enable 0x02D5D6E0 run
    unstubbed on a fake GroundModule / handle / ground: the words they leave are the hydrant's in the user's log
    (log_v15_hydrant: S4CE tag=2 ground +0x68 / +0x6C FFFFFFFF, +0x70 00320100 (+0x72 1); S4CG +0xF8 01000001 (+0xFB 1);
    S4CH handle +0x160 001E0101 (+0x163 1)), where v1.1's (gm, 0) left the skeleton's at 0 (tag=1)"""
    e = Run(patched)

    def fake():
        gm = e.alloc(0x200, b'\0')
        e.setw(gm, C.SK_GM_VT)
        obj = e.alloc(0x300, b'\0')                    # its +0x18 object (+0x234 no handle of its own)
        e.setw(gm + 0x18, obj)
        e.mu.mem_write(gm + 0xF8, b'\x01\x00\x00\x00')
        h = e.alloc(0x200, b'\0')
        e.setw(gm + 0xF0, h)
        e.setw(h + 0x160, 0x001F0100)
        g = e.alloc(0x100, b'\0')
        e.setw(h, g)
        e.setw(g + 0x70, 0x00330000)
        e.setw(g + 0x74, 0x01000100)                    # +0x74 1: the first vertex loop (0x10551DD8's offsets)
        vs = [e.alloc(0x40, b'\0') for _ in range(2)]
        for i, v in enumerate(vs):
            e.setw(v + 4, vs[(i + 1) % 2])
            e.mu.mem_write(v + 8, struct.pack('>2f', -46.2 + 12 * i, 28.0))
        e.setw(g + 0x34, 2)
        e.setw(g + 0x3C, vs[0])
        return gm, h, g

    def words(gm, h, g):
        return ('%08X' % e.w(g + 0x68), '%08X' % e.w(g + 0x6C), e.mu.mem_read(g + 0x72, 1)[0],
                e.mu.mem_read(gm + 0xFB, 1)[0], e.mu.mem_read(h + 0x163, 1)[0])
    gm, h, g = fake()
    e.call(C.GC_ENABLE, gm)
    check('skeleton v1.2 (the game\'s code): GC_ENABLE with +0xFB 0 (v1.1: GC_ON (gm, 0)) leaves the ground off, as the '
          'user\'s log showed for the skeleton (+0x68 / +0x6C 0, +0x72 0, +0xFB 0, +0x163 0)',
          words(gm, h, g), ('00000000', '00000000', 0, 0, 0))
    e.call(C.GC_ON, gm, 1)
    e.call(C.GC_ENABLE, gm)
    got = words(gm, h, g)
    check('skeleton v1.2 (the game\'s code): GC_ON (gm, 1) then GC_ENABLE: the hydrant\'s logged words (ground +0x68 / '
          '+0x6C FFFFFFFF, +0x72 1, gm +0xFB 1, handle +0x163 1)', got, ('FFFFFFFF', 'FFFFFFFF', 1, 1, 1))
    check('skeleton v1.2: ... its vertices\' last places set (+0x32 1)',
          [e.mu.mem_read(e.w(g + 0x3C) + 0x32, 1)[0], e.mu.mem_read(e.w(e.w(g + 0x3C) + 4) + 0x32, 1)[0]], [1, 1])
    e.setw(g + 0x68, 0x12345678)
    e.call(C.GC_ENABLE, gm)
    check('skeleton v1.2: GC_ENABLE again (every moved frame): nothing rewritten once on (+0x163 1)',
          '%08X' % e.w(g + 0x68), '12345678')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    diag = '--diag' in sys.argv
    base, patched = args[0], args[1]
    fa = [a[11:] for a in sys.argv[1:] if a.startswith('--features=')]
    feats = C.RELEASE if not fa else frozenset(f for f in fa[0].split(',') if f)
    print('features: %s' % (','.join(sorted(feats)) or '(safe)'))
    out, info = words_checks(base, patched, diag, feats)
    img = K.Image(base)
    e = Run(patched)
    if diag:
        e.osr_full = []
        e.stub(C.OSREPORT_VENEER, lambda e_: (e_.rec('osr', 3, 4, 5, 6),
                                               e_.osr_full.append(tuple(e_.r(i) for i in range(3, 11))))[1])
    e.stub(C.MSG_HANDLE, lambda e_: e_.calls.append(('msg_handle', e_.r(5), e_.r(6))))

    def msg_send(e_):
        m = e_.r(4)
        inner = e_.w(e_.w(m + 8))
        e_.calls.append(('msg_send', e_.w(m), e_.w(m + 4), e_.w(inner), e_.w(inner + 4)))
    e.stub(C.MSG_SEND, msg_send)
    weapon_checks(e, img, info, diag)
    sway_checks(e, info)
    hitcheck_checks(e, info, diag)
    burn_checks(e, info, diag)
    clear_checks(e, info, diag)
    info['img'] = img
    skeleton_checks(e, info, diag)
    pb_checks(patched, info, diag)
    ccol_checks(patched, info, diag)
    burn2_checks(e, info, diag)
    if 'skeleton' in feats:
        col_on_checks(patched)
    pose_checks(e, info, diag)
    skdist_checks(e, info)
    shalf_checks(e, info)
    ice_checks(e, info, diag)
    bgrav_checks(e, info, diag)
    fighter_desc_checks(e, img, info)
    g1_checks(e, info)
    s13_checks(e, info)
    s42_checks(e, info)
    s43_checks(e, info)
    hud_checks(e, info)
    plyc_checks(e, info, diag)
    panel_checks(e, info, diag)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
