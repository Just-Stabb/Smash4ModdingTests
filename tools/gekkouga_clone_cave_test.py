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


def check(what, got, want):
    global fails, checks
    checks += 1
    ok = got == want
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
        C.POLL_SLOTS if 'hurt' in F or diag else (0x94,) if F & {'sway', 'hitcheck', 'burn'} else ())
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
    check('his articles 0-5 as before, 6 / 7 the clones (0x1A1, max 1, no spawner)', rows,
          vrows + [[C.CLONE_KIND, 1, 0, 0], [C.CLONE_KIND, 1, 0, 0]] +
          ([[C.SK_KIND, 1, 0, 0]] if 'skeleton' in info['feats'] else []))
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
    e.setw(mm + C.MM_MOTION, motion)
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
    check('burn: every move\'s instance, unshielded and shielded, totals at least %s %% (the user\'s floor): %s' % (
        C.BURN_MIN_TOTAL, ', '.join('%d %.2f / %.2f' % (m[0], C.burn_total(m), C.burn_total(m, True)) for m in C.BURN_MOVES)),
          [(m[0], sh) for m in C.BURN_MOVES for sh in (False, True) if C.burn_total(m, sh) < C.BURN_MIN_TOTAL - 1e-4], [])
    check('burn: the shield clamp only where 50 %% / %d %% falls under the floor; above it the rule exact' % round(100 * C.BURN_SHIELD_DAMAGE),
          [m[0] for m in C.BURN_MOVES if (C.burn_shield_damage(m) != m[1] * C.BURN_SHIELD_DAMAGE)
           != (m[1] * C.BURN_SHIELD_DAMAGE * (C.burn_shield_frames(m) // m[2]) < C.BURN_MIN_TOTAL)], [])
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
    sd = round(C.burn_shield_damage(C.BURN_MOVES[0]), 4)
    check('burn: a shielded hit: half the frames (120), %d %%%% of the damage raised to the 3 %%%% total (%s a tick), its own '
          'timer' % (round(100 * C.BURN_SHIELD_DAMAGE), sd), inst(4), [(237, 3, 6, 2, 0.4), (119, 5, 6, 2, sd)])
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
        e.mu.mem_write(A['bproc'], b'\x07' * (C.BURN_CONTEXTS * C.BURN_ENTS))
    for i in range(16):
        e.setw(A['gk_hide'] + 4 * i, 3)
    for i in range(C.SLOTS):
        e.setw(A['gk_tags'] + 4 * i, 9)
        e.setw(A['gk_plyr'] + 4 * i, 2)
    n0 = e.w(A['gk_clr'])
    e.mu.reg_write(RG[10], 0x10)
    e.call(lab['gk_clear'], 0x12345678, until=C.CLEAR_BACK)
    check('burn v1.2: gk_clear back at CLEAR_BACK with r3 / r10 kept', (e.r(3), e.r(10)), (0x12345678, 0x10))
    if burn:
        check('burn v1.2: every burn of the last match gone, the processed counts 0',
              (any(e.w(A['btab'] + k) for k in range(0, C.SLOTS * C.BURN_CAP * 16, 4)),
               bytes(e.mu.mem_read(A['bproc'], C.BURN_CONTEXTS * C.BURN_ENTS)).strip(b'\0')), (False, b''))
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
              (round(C.burn_total(sk_row), 3), round(C.burn_shield_damage(sk_row), 4), round(C.burn_total(sk_row, True), 3)),
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
    check('his article list: 9 entries, article 8 the skeleton (one at a time)',
          (e.w(lst + 4), [e.w(e.w(lst) + 16 * 8 + 4 * j) for j in range(4)]), (9, [C.SK_KIND, 1, 0, 0]))
    # ---- the game's side, stubbed
    calls = []
    st = dict(file=1, ground=1)
    mgr = e.alloc(0x40, b'\0')
    e.setw(C.RES_MGR, mgr)
    e.setw(mgr + 0x30, 0xABC0)
    gm = e.alloc(0x200, b'\0')
    e.setw(gm, C.SK_GM_VT)
    ground = e.alloc(0x200, b'\0')

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
        return lambda e_: calls.append((name, e_.r(3), e_.r(4)) + tuple(round(x, 3) for x in struct.unpack(
            '>2f', bytes(e_.mu.mem_read(e_.r(5), 8)))))

    def gc_free(e_):
        calls.append(('col_free', e_.r(3)))
        e_.setw(e_.r(3) + 0xF0, 0)
    e.stub(C.RES_GET, res_get)
    e.stub(C.RES_FIND, res_find)
    e.stub(C.RES_ASSIGN, lambda e_: calls.append(('assign', e_.r(3), e_.w(e_.r(4)))))
    e.stub(C.RES_FREE, lambda e_: calls.append(('res_free', e_.r(4))))
    e.stub(C.GC_MAKE, gc_make)
    e.stub(C.GC_ON, lambda e_: calls.append(('on', e_.r(3), e_.r(4))))
    e.stub(C.GC_SETV, vert('setv'))
    e.stub(C.GC_MOVEV, vert('movev'))
    e.stub(C.GC_COMMIT, lambda e_: calls.append(('commit', e_.r(3))))
    e.stub(C.GC_FREE, gc_free)
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
    sv.update({0x0F000300 + v: 9.0 for v in range(11)})
    del calls[:]
    e.call(lab['sk_start'], 0, weapon, 0)
    check('skeleton start: a last life\'s grounds removed (its GroundModule: the hydrant\'s class), VARs 0-10 = 0',
          (calls, [sv[0x0F000300 + v] for v in range(11)]), ([('col_free', gm)], [0.0] * 11))
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
    want_v = [(gm, i, 50.0 + vx, 10.0 + vy) for i, (vx, vy) in enumerate(C.SK_VERTS)]
    check('skeleton collision: as the hydrant\'s set-up: its kind\'s bundle (manager +0x30, kind 0x1A2, 0, 0), '
          '"skeleton.lvd" in it, GroundModule +0xEC = the file, the grounds made (gm, 1, 0, 0), its 4 vertices placed at '
          'it (x +- 6, y + 2 / + 28), the lines recomputed, on (gm, 0), both handles released',
          c1, [('res_get', 0xABC0, C.SK_KIND, 0, 0), ('res_find', 0x1111, 'skeleton.lvd', 1), ('assign', gm + 0xEC, 0x2222),
               ('make', gm, 1, 0, 0)] + [('setv',) + v for v in want_v] +
              [('commit', gm), ('on', gm, 0), ('res_free', 2), ('res_free', 2)])
    check('skeleton collision: VAR_6 = 1 (made)', sv[C.SK_VAR_COL], 1.0)
    check('skeleton: running, its stand-in body x %g (PostureModule vt +0xE4)' % C.SK_SCALE, scales, [('scale', post, C.SK_SCALE)])
    if diag:
        check('skeleton diag: S4SC state 1, its first ground', [x[:2] for x in logs('gk_fsc')], [(1, ground)])
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.7, 10.0))
    c2 = frame()
    check('skeleton collision: it moved 0.7: its vertices moved (riders carried: the move call), the lines recomputed',
          c2, [('movev', gm, i, round(50.7 + vx, 3), 10.0 + vy) for i, (vx, vy) in enumerate(C.SK_VERTS)] + [('commit', gm)])
    e.setw(ground + 0x160, 0xFFFF0000)
    check('skeleton collision: its ground gone (id -1): nothing moved', frame(), [])
    e.setw(ground + 0x160, 0)
    e.mu.mem_write(post + 0x10, struct.pack('>2f', 50.0, 10.0))
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
    near = (54.0, 20.0, 60.0, 25.0)
    far = (200.0, 0.0, 210.0, 5.0)
    e.mu.mem_write(other['f'] + 0x1E, b'\x00')
    e.setw(team + 8, 0)
    a = attacker(4, 1, [(1, near), (1, far)])            # slot 5, another team: entry 0 over it (9 %), entry 1 away
    e.hs_ret = 5
    frame()
    check('skeleton hit: slot 5\'s entry 0 over it: VAR_4 9 (its damage), VAR_9 1 hit, the place (its X 60 kept in the '
          'box: 56, its Y 12 + 8 = 20)', [sv.get(v) for v in (C.SK_VAR_DMG, C.SK_VAR_HITS, C.SK_VAR_HX, C.SK_VAR_HY)],
          [9.0, 1.0, 56.0, 20.0])
    check('skeleton hit: the attacker\'s hitlag (HITSTOP_FN on that hitbox, 5 frames on its StopModule)',
          ([c[1:3] for c in e.calls if c[0] == 'hitstop'], [c for c in e.calls if c[0] == 'sk_stop']),
          ([(a['acc'], a['data'])], [('sk_stop', a['stop'], 5, 1)]))
    if diag:
        check('skeleton diag: S4SH (owner 3, attacker 0x05, hitbox 0, 90, HP left 160, at 56, 20)', logs('gk_fsh'),
              [(3, 5, 0, 90, 160, 56, 20)])
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
    # unowned: nothing
    sv.clear()
    check('skeleton: nobody asked for it: no owner, nothing', (frame(), sv.get(C.SK_VAR_SLOT, 0.0)), ([], 0.0))
    for i in range(8):
        e.mu.mem_write(e.entries + C.ENTRY * i + 0x1E, b'\x00')
    e.hs_ret = 7


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
    check('v6 gauge colours: as is / blue / grey', bytes(e.mu.mem_read(A['ctf'], 48)),
          b''.join(struct.pack('>4B4h', *c) for c in C.GAUGE_COLOURS))
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
        name = [n for n, a_ in atoms.items() if a_ == atom][0]
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
    check('v7: the next frame the rings turn on (2 x speed, kept in 0-360), the full charge on frame 11',
          [c[2] for c in r if c[0] in ('rotate', 'goto')],
          [round((2 * sp) % 360.0, 2) for sp in C.GAUGE_SPEEDS] + [11])
    check('v7: the ability (2050): blue', [c for c in run2(2050) if c[0] == 'colour'], [('colour', clips['gkgauge_mc'], A['ctf'] + 24)])
    check('v7: nothing (0): the gauge hidden, no ring calls', run2(0), [('visible', ko, 0), ('visible', clips['gkgauge_mc'], 0)])
    check('v7: the names interned each frame from the atom pool', [c for c in e.calls if c[0] == 'intern'][:1], [('intern', 'gkgauge_mc', True)])
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
