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


def words_checks(base, patched, diag):
    out, info = C.build(base, diag)
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


def weapon_checks(e, img, info):
    L, A, lab = info['layout'], info['A'], info['labels']
    d = e.call(W.DESC_SWITCH, 0, C.CLONE_KIND)
    check('the weapon descriptor getter: kind 0x1A1 -> its descriptor', d, A['w_desc'])
    check('its bytes: bunshin\'s but +8 (its motion info)',
          [e.w(d + 4 * i) for i in range(L['dsize'] // 4) if i != 2],
          [img.w(L['bdesc'] + 4 * i) for i in range(L['dsize'] // 4) if i != 2])
    mi = e.w(d + 8)
    check('its motion info: his 668 motions', (mi, e.w(mi + 4)), (A['w_minfo'], 668))
    ents = e.w(mi)
    check('the entries: his body motions\' hashes and flags (v2: his fighter motion table\'s entries)',
          [(e.w(ents + 8 * i), e.w(ents + 8 * i + 4)) for i in range(668)], L['ents'])
    his = img.w(C.GK_DESC + 4)
    check('his motion table: 668 entries, hashes the v1 list', ([h for h, _f in L['ents']] == L['hashes'], len(L['ents'])),
          (True, 668))
    check('v2: its motion info\'s words 2-5 are his (parts 0x10378F70 x 6, groups 0x10378FA0 x 5)',
          [e.w(mi + 4 * i) for i in range(2, 6)], [img.w(his + 4 * i) for i in range(2, 6)])
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
    VT_OURS = (0x1C, W.HIT_METHOD) + C.POLL_SLOTS
    check('its vtable: bunshin\'s but +0x1C / +0x64 / +0x84 / +0x8C / +0x94 / +0xAC (v3)',
          [e.w(vt + o) for o in range(0, L['vsize'], 4) if o not in VT_OURS],
          [img.w(L['svt'] + o) for o in range(0, L['vsize'], 4) if o not in VT_OURS])
    check('its +0xAC: the hit method, +0x1C the set-up, the 4 phases\' pollers',
          [e.w(vt + o) for o in (W.HIT_METHOD, 0x1C) + C.POLL_SLOTS],
          [lab['w_hit'], lab['w_init']] + [lab['wp_%X' % o] for o in C.POLL_SLOTS])
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
    e.stub(hmset, hm_fn)
    hm = e.alloc(0x20, b'\0')
    e.setw(hm, hmvt)
    e.setw(cacc + C.W_HIT_MOD, hm)
    e.calls = []
    e.call(lab['w_init'], s, weapon)
    check('v3 set-up (+0x1C): HitModule vt +0x4C(&{his 8 hurtboxes, 8}, 0)', e.calls, [('hurt', hm, A['hurt'], 8, 0)])
    check('... the hurtbox data: his vl group 5 entries, bones 0x7D0 + his joint, pool 2',
          bytes(e.mu.mem_read(A['hurt'], 0x30 * 8)) == C.hurt_blob() and
          [struct.unpack_from('>I', C.hurt_blob(), 0x30 * i + 0x1C)[0] for i in range(8)] ==
          [0x7D0 + j for j in (12, 19, 22, 16, 8, 4, 9, 5)], True)
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
        return [c for c in e.calls if c[0] in ('dmg', 'setf') or c[0].startswith('orig')], e.set_wm, e.kept()
    e.mu.mem_write(owner['f'] + 0x1E, b'\x04')
    e.clone_vars[C.VAR_SLOT] = 3.0
    for o in C.POLL_SLOTS:
        check('v3 poller +0x%X, no damage: nothing set, bunshin\'s method with the same arguments' % o, poll(o, 0.0),
              ([('dmg', 0), ('orig%X' % o, s, weapon, 0x55, 0x66)], [], True))
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
    want = [img.w(W.MODULE_TABLE + 0x70 * C.TEMPLATE + 4 * j) for j in range(28)]
    check('v3: its row: the template kind\'s (lizardonm, 0x15C: bunshin\'s modules + Kinetic, Attack, Hit, Damage)',
          [e.w(row + 4 * j) for j in range(28)], want)
    T_ = info['T']
    check('v3: its base kind (the weapon switches\' templates): 0x15C', e.w(T_['bt'] + 4 * (C.CLONE_KIND - W.OLD_N)), C.TEMPLATE)
    nt = dict(W.NAME_TABLES)
    check('... 0x15C is lizardon\'s lizardonm', (img.cstr(img.w(nt['owner'] + 4 * C.TEMPLATE)),
                                                 img.cstr(img.w(nt['name'] + 4 * C.TEMPLATE))), C.TEMPLATE_NAME)
    e.mu.reg_write(REGS[30], CLONE_OTHER)
    e.call(mr)
    check('the module set-up: bunshin\'s own row as before', e.r(8), 0x70 * CLONE_OTHER)
    T = info['T']
    check('owner "gekkouga", name / folder "clone"',
          [e.cstr(e.w(T[n] + 4 * C.CLONE_KIND)) for n in ('owner', 'name', 'folder')], ['gekkouga', 'clone', 'clone'])
    check('root and static tables: bunshin\'s',
          (e.w(T['root'] + 4 * C.CLONE_KIND), e.w(T['u32'] + 4 * C.CLONE_KIND),
           struct.unpack('>H', bytes(e.mu.mem_read(T['u16'] + 2 * C.CLONE_KIND, 2)))[0],
           bytes(e.mu.mem_read(T['u8'] + C.CLONE_KIND, 1))[0]),
          (img.w(W.NAME_TABLES[0][1] + 4 * C.CLONE_BASE), img.w(W.STATIC_TABLES[0][1] + 4 * C.CLONE_BASE),
           img.h(W.STATIC_TABLES[2][1] + 2 * C.CLONE_BASE), img.b(W.STATIC_TABLES[1][1] + C.CLONE_BASE)))
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
          vrows + [[C.CLONE_KIND, 1, 0, 0], [C.CLONE_KIND, 1, 0, 0]])
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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    diag = '--diag' in sys.argv
    base, patched = args[0], args[1]
    out, info = words_checks(base, patched, diag)
    img = K.Image(base)
    e = Run(patched)
    if diag:
        e.stub(C.OSREPORT_VENEER, lambda e_: e_.rec('osr', 3, 4, 5))
    weapon_checks(e, img, info)
    fighter_desc_checks(e, img, info)
    g1_checks(e, info)
    s13_checks(e, info)
    s42_checks(e, info)
    s43_checks(e, info)
    hud_checks(e, info)
    print('%d checks, %d failures' % (checks, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
