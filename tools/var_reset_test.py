#!/usr/bin/env python3
"""Tests tools/var_reset_cave.py (exe_v46w_vars: New_Var's Reset, Var_Reset_Set, the MSC selection IDs) in the patched
RPX (unicorn), against the executable it was built on.

  python3 tools/var_reset_test.py exe_v46w_vars.rpx exe_v46v_threads.rpx

- the words: every hook site held what the cave expects in BASE and its branch in PATCHED; the region was free; the
  text region; the code in place;
- the command tables: Var_Reset_Set's CRC -> index 2000 through the game's binary search (vanilla and acmd_ext's
  commands keep theirs, an unknown CRC -1), both loader loops step over it (5 words) between vanilla / acmd_ext
  commands, the interpreter's fetch gives vr_cmd for it and the old handlers for every other index;
- the events, each from its hook site with the game's own code around it (the fighters' WorkModule set_float through
  position_vars' / acmd_ext's hooks; gs_hit with the damage decision stubbed; the object set-up chain): KO (Dead
  0xB1), landing (situation 2 -> 0), ledge (0x72 / 0x73 / 0xF3 / 0xF4 from another status), hit (a reaction: yes;
  armor: no) each write only the items with their bit, only on the object it happened to; not on 1 -> 0, 0 -> 2,
  a status kept, 0x72 -> 0x73; KO once per KO (Dead then the set-up: one write), the set-up fires a KO item that
  hasn't fired and frees the list;
- New_Var's Reset (bits 8-11 of Scope): Initial (an int one truncated) put back; Scope's word restored; Reset 0 ->
  New_Var exactly as exe_v46v (the variables' memory after the same scripts compared with BASE's h_newvar), no list;
  a later New_Var with Reset 0 removes the item; not executed: nothing;
- Var_Reset_Set: on this object, on a player slot's fighter (Owner 4 = slot 2: its own VAR_24 back on its hit), a
  cross-object item (the owner's KO writes another fighter's variable: SLOT2_SHARED_0), Reset 0 removes, steps 20;
- MSC: 0x0F0003CA / CB / CC / CD through the real set_float / get_float: select, set, read the mask, remove;
- the list full (31 items): refused and counted; writes ignored while an event writes (busy);
- no items: an event changes nothing (the old behaviour).
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch as R  # noqa: E402
import var_reset_cave as V  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_7, UC_PPC_REG_0, UC_PPC_REG_12, UC_PPC_REG_29, UC_PPC_REG_FPR1,
                               UC_PPC_REG_LR, UC_PPC_REG_MSR)

fails = 0


class C:        # acmd_ext_cave.py's state in exe_v46v_threads (not imported: that file may grow commands later)
    OBJS, OBJ_N, OBJ_SIZE, NV_POOL, ACC_CACHE = 0x04B94000, 48, 0x100, 0x04BD0000, 0x04B97000
    NV_OFF = NV_POOL - OBJS
    FIGHTERS, FIGHTER_ENTRY = 0x1035184C, 0x76B0
    NEW_BASE = V.EXT_NEW_BASE
    COMMANDS = [(n, 11 if n == 'New_Var' else None) for n in V.EXT_V46V_COMMANDS]


MEM = 0x30000000                                # (position_vars checks pointers to 0x10000000-0x4FFFFFFF)
FGET, FSET = 0x02F1DBE4, 0x02F1DC04              # the fighters' WorkModule get_float / set_float
CRC_TABLE, COUNT, SIZES, HANDLERS = 0x100FAAB8, 584, 0x100FA198, 0x10350ED8
NV = lambda k: 0x0F000380 + k                    # noqa: E731
VAR = lambda k: 0x0F000300 + k                   # noqa: E731
TIMER = lambda k: 0x0F000320 + k                 # noqa: E731
REG = lambda n: UC_PPC_REG_3 + n - 3             # noqa: E731


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def fb(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def run(mu, start, stop, regs, count=2000000):
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(start, stop, count=count)


def f2bits(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def call(mu, fn, r3=0, r4=0, r5=0, f1=0.0):
    """fn(r3, r4, r5, f1) -> (r3, f1); callee-saved r14-r31 must survive"""
    mu.reg_write(UC_PPC_REG_FPR1, f2bits(f1))
    for r in range(14, 32):
        mu.reg_write(REG(r), 0x1000 + r)
    run(mu, fn, RET, {UC_PPC_REG_3: r3, UC_PPC_REG_4: r4, UC_PPC_REG_5: r5})
    bad = [r for r in range(14, 32) if mu.reg_read(REG(r)) != 0x1000 + r]
    assert not bad, 'clobbered r%s (0x%08X)' % (bad, fn)
    return (mu.reg_read(UC_PPC_REG_3),
            round(struct.unpack('>d', struct.pack('>Q', mu.reg_read(UC_PPC_REG_FPR1)))[0], 4))


def main():
    patched, base = sys.argv[1:3]
    om, pm = machine(base), machine(patched)
    orig = V.rpx_reader(base)
    out, L = V.build(orig)
    E = V.ext_labels()

    # ---- words
    check('patched: every word the cave writes', [hex(a) for a, w in sorted(out.items()) if r32(pm, a) != w], [])
    check('base: the region was free (code, data, lists)',
          [hex(a) for a in range(V.VR_CODE, V.VR_END, 4) if orig(a) != 0][:3], [])
    check('base: hook words', {a: orig(a) for a in (V.STATUS_AT, V.SIT_AT, L['gs_hit_site'], L['nv_slot'],
                                                     E['lk_none'], E['s1_orig'], E['s2_orig'], E['f_orig'])},
          {V.STATUS_AT: V.STATUS_WORD, V.SIT_AT: V.SIT_WORD, L['gs_hit_site']: V.HIT_WORD, L['nv_slot']: E['h_newvar'],
           E['lk_none']: 0x3860FFFF, E['s1_orig']: 0x7C0A202E, E['s2_orig']: 0x7D8BF02E, E['f_orig']: 0x54E6103A})
    check('the set-up and bv_zero chains kept', (L['reset_chain'] == V.b_target(V.RESET_AT, orig(V.RESET_AT)),
                                                 L['var_chain']), (True, E['ue_zero']))
    for name, path in (('base', base), ('patched', patched)):
        d, _s, _e, secs = R.load(path)
        info = R.section_data(d, next(s for s in secs if s[1] == R.SHT_RPL_FILEINFO))
        region = struct.unpack('>I', info[4:8])[0]
        check('%s: text region' % name, hex(region), '0x2bd6000' if name == 'base' else hex(V.TEXT_REGION))

    # ---- the command tables
    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    check('Var_Reset_Set\'s CRC is in no table', V.CMD_CRC in dict(pairs) or V.CMD_CRC in
          [zlib.crc32(c[0].encode()) & 0xFFFFFFFF for c in C.COMMANDS], False)
    check('Var_Reset_Set -> index %d' % V.VR_INDEX, lookup(pm, V.CMD_CRC), V.VR_INDEX)
    check('vanilla CRCs keep their index', [hex(c) for c, i in pairs[::7] if lookup(pm, c) != i], [])
    new = [(zlib.crc32(c[0].encode()) & 0xFFFFFFFF, C.NEW_BASE + k) for k, c in enumerate(C.COMMANDS)]
    check('acmd_ext\'s commands keep theirs', [lookup(pm, c) for c, _ in new], [i for _, i in new])
    check('an unknown CRC -> -1', lookup(pm, 0x12345678), 0xFFFFFFFF)
    BUF = 0x7F004000
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    nvk = [c[0] for c in C.COMMANDS].index('New_Var')
    script = [0xB738EABD, V.CMD_CRC, new[nvk][0], V.CMD_CRC, 0x42ACFE7D]
    want_idx = [idx[0xB738EABD], V.VR_INDEX, new[nvk][1], V.VR_INDEX, idx[0x42ACFE7D]]
    want_size = [size[want_idx[0]], 5, C.COMMANDS[nvk][1], 5, size[want_idx[4]]]
    from unicorn.ppc_const import UC_PPC_REG_28, UC_PPC_REG_30
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_29: 0, UC_PPC_REG_30: len(script), UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script), UC_PPC_REG_30: SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, s in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += s
        run(pm, start, stop, regs)
        check('loader %d: indices' % (loop + 1), [r32(pm, BUF + 4 * x) for x in offs], want_idx)
        check('loader %d: words stepped (Var_Reset_Set 5)' % (loop + 1),
              pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4), sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0), mu.reg_read(UC_PPC_REG_12)
    check('fetch: index 2000 -> vr_cmd, r12 kept', fetch(pm, V.VR_INDEX), (L['vr_cmd'], 0x55))
    check('fetch: vanilla handlers unchanged', [i for _, i in pairs[::5] if fetch(pm, i)[0] != r32(om, HANDLERS + 4 * i)], [])
    check('fetch: acmd_ext\'s handlers (New_Var -> vr_newvar)', [fetch(pm, i)[0] for _, i in new],
          [r32(om, E['cmd_handlers'] + 4 * k) if k != nvk else L['vr_newvar'] for k in range(len(new))])

    # ---- objects: two fighters (accessor +0x20 StatusModule (fighters' vtable, +0x9C the fighter, whose +0x28 is the
    # accessor), +0x28 WorkModule (fighters' vtable)) and an article
    pm.mem_map(MEM, 0x200000)
    om.mem_map(MEM, 0x200000)

    def obj(mu, at, fighter=True):
        acc, wm, cats, sm, fo = at, at + 0x100, at + 0x200, at + 0x300, at + 0x400
        w32(mu, acc + 0x28, wm)
        w32(mu, wm, 0x1013A1C0 if fighter else 0x10003224)
        w32(mu, wm + 8, cats)
        w32(mu, acc + 0x20, sm)
        w32(mu, sm, V.FIGHTER_SM_VT if fighter else 0x10002854)
        w32(mu, sm + 0x9C, fo)
        w32(mu, fo + 0x28, acc)
        w32(mu, acc + 0x18, at + 0x500)                     # a PostureModule (position_vars' slot lookup needs one)
        return acc, wm, sm
    me, me_wm, me_sm = obj(pm, MEM + 0x10000)
    foe, foe_wm, foe_sm = obj(pm, MEM + 0x11000)
    art, art_wm, art_sm = obj(pm, MEM + 0x12000, fighter=False)
    for k, (wm, acc) in enumerate(((me_wm, me), (foe_wm, foe), (art_wm, art))):     # acc_of's cache (the frame hook's)
        w32(pm, C.ACC_CACHE + 8 * k, wm)
        w32(pm, C.ACC_CACHE + 8 * k + 4, acc)
    tab, ents = MEM + 0x60000, MEM + 0x61000                # fighter table: slot 1 me, slot 2 foe
    w32(pm, C.FIGHTERS, tab)
    w32(pm, tab, tab + 0x10)
    w32(pm, tab + 0x10, ents)
    w32(pm, tab + 0x18, 2)
    for k, (ident, acc) in enumerate(((0x10000, me), (0x20000, foe))):
        e = ents + k * C.FIGHTER_ENTRY
        w32(pm, e, ident)
        w32(pm, e + 0xC, acc)
        pm.mem_write(e + 0x1E, b'\4')

    def fget(wm, ident):
        return call(pm, FGET, wm, ident)[1]

    def fset(wm, ident, v):
        call(pm, FSET, wm, ident, f1=v)

    def blk(wm):
        for i in range(V.VR_N):
            if r32(pm, V.VR_TAB + V.VR_BLK * i) == wm:
                return V.VR_TAB + V.VR_BLK * i
        return None

    def items(wm):
        b = blk(wm)
        if b is None:
            return {}
        got = {}
        for i in range(V.VR_ITEMS):
            ident, val, mask = struct.unpack('>IfI', pm.mem_read(b + 0x10 + 0x10 * i, 12))
            if ident:
                got[ident] = (round(val, 4), mask)
        return got

    def cnt(k):
        return r32(pm, V.VR_DATA + V.D_CNT + 4 * k)

    def put(wm, ident, mask, v):
        return call(pm, L['vr_put'], wm, ident, mask, f1=v)[0]

    def snap():
        return (bytes(pm.mem_read(C.OBJS, C.OBJ_N * C.OBJ_SIZE)) + bytes(pm.mem_read(C.NV_POOL, C.OBJ_N * C.OBJ_SIZE)) +
                bytes(pm.mem_read(V.VR_TAB, V.VR_N * V.VR_BLK)))

    def chg(sm, old, new):
        w32(pm, sm + 0x48, old)
        run(pm, V.STATUS_AT, V.STATUS_AT + 4, {REG(28): new, REG(30): sm})
        return r32(pm, sm + 0x48)

    def sit(sm, old, new):
        w32(pm, sm + 0x88, old)
        w32(pm, sm + 0x84, old)
        run(pm, V.SIT_AT, V.SIT_AT + 4, {REG(28): new, REG(29): sm})
        return r32(pm, sm + 0x84)

    DECISION = MEM + 0x70000                                # the damage reaction decision, stubbed: its result
    w32(pm, 0x02E76BB8, 0x3C600000 | (DECISION >> 16))      # lis r3, DECISION@h
    w32(pm, 0x02E76BBC, 0x80630000 | (DECISION & 0xFFFF))   # lwz r3, DECISION@l(r3)
    w32(pm, 0x02E76BC0, 0x4E800020)                         # blr (written once: unicorn keeps translated code)

    def hit(acc, result):
        w32(pm, DECISION, result)
        return call(pm, E['gs_hit'], 0, acc)[0]

    def setup(acc):
        run(pm, V.RESET_AT, V.RESET_AT + 4, {REG(31): acc})

    # ---- nothing kept: events change nothing
    fset(me_wm, VAR(0), 5.0)
    s0 = snap()
    chg(me_sm, 0x0, V.DEAD)
    sit(me_sm, 2, 0)
    chg(me_sm, 0x0, 0x72)
    check('no reset items: the gs_hit path returns the decision (0)', hit(me, 0), 0)
    check('no reset items: KO / landing / ledge / hit change nothing', snap() == s0, True)
    check('... and the status / situation stored', (r32(pm, me_sm + 0x48), r32(pm, me_sm + 0x84)), (0x72, 0))

    # ---- one item per event on me, the same on foe
    def arm():
        for wm in (me_wm, foe_wm):
            fset(wm, VAR(1), 11.0)
            fset(wm, VAR(2), 12.0)
            fset(wm, TIMER(3), 13.0)
            fset(wm, NV(4), 14.0)
            fset(wm, NV(5), 15.0)
            put(wm, VAR(1), V.KO, 1.5)
            put(wm, VAR(2), V.LANDING, 2.5)
            put(wm, TIMER(3), V.LEDGE, 3.0)
            put(wm, NV(4), V.HIT, 4.5)
            put(wm, NV(5), V.LANDING | V.LEDGE, -1.0)

    def vals(wm):
        return [fget(wm, i) for i in (VAR(1), VAR(2), TIMER(3), NV(4), NV(5))]
    armed = [11.0, 12.0, 13.0, 14.0, 15.0]
    arm()
    check('items kept (ID, value, mask)', items(me_wm), {VAR(1): (1.5, 1), VAR(2): (2.5, 2), TIMER(3): (3.0, 4),
                                                         NV(4): (4.5, 8), NV(5): (-1.0, 6)})
    sit(me_sm, 2, 0)
    check('landing (2 -> 0): VAR_2 and the landing|ledge New_Var only', vals(me_wm), [11.0, 2.5, 13.0, 14.0, -1.0])
    check('... the other fighter untouched', vals(foe_wm), armed)
    arm()
    for o, n in ((1, 0), (0, 2), (2, 1), (0, 0), (2, 2)):
        sit(me_sm, o, n)
    check('no landing: 1 -> 0, 0 -> 2, 2 -> 1, kept', vals(me_wm), armed)
    chg(me_sm, 0x0, 0x72)
    check('ledge (CliffCatchMove 0x72): TIMER_3 and the New_Var', vals(me_wm), [11.0, 12.0, 3.0, 14.0, -1.0])
    arm()
    chg(me_sm, 0x72, 0x73)
    chg(me_sm, 0x73, 0x73)
    check('0x72 -> 0x73 (the same grab), 0x73 kept: nothing', vals(me_wm), armed)
    for k in (0x73, 0xF3, 0xF4):
        arm()
        chg(me_sm, 0x11, k)
        check('ledge 0x%X from another status' % k, vals(me_wm)[2], 3.0)
    arm()
    check('a hit with no reaction (armor: the decision 1) passes it on', hit(me, 1), 1)
    check('... and writes nothing', vals(me_wm), armed)
    check('a hit that takes effect (0) passes it on', hit(me, 0), 0)
    check('... the hit item only', vals(me_wm), [11.0, 12.0, 13.0, 4.5, 15.0])
    check('... the other fighter untouched', vals(foe_wm), armed)
    arm()
    chg(me_sm, 0x45, V.DEAD)
    check('KO (Dead): VAR_1 only', vals(me_wm), [1.5, 12.0, 13.0, 14.0, 15.0])
    check('... its KO bit dropped: the item freed (no other bit)', VAR(1) in items(me_wm), False)
    check('... the other items kept', sorted(items(me_wm)), sorted([VAR(2), TIMER(3), NV(4), NV(5)]))
    chg(me_sm, V.DEAD, V.DEAD)
    check('the same status again: nothing', vals(me_wm)[0], 1.5)
    check('event counters (KO, landing, ledge, hit)', [cnt(k) >= 1 for k in range(4)], [True] * 4)

    # KO once per KO: Dead, then the set-up: one write; an item Dead didn't fire (put after it) fires at the set-up
    put(me_wm, VAR(6), V.KO | V.LANDING, 6.0)
    fset(me_wm, VAR(6), 66.0)
    chg(me_sm, 0x0, V.DEAD)
    check('KO|landing item: written at Dead, KO bit dropped, kept for landing', (fget(me_wm, VAR(6)), items(me_wm)[VAR(6)]),
          (6.0, (6.0, 2)))
    fset(me_wm, VAR(6), 77.0)
    put(me_wm, VAR(7), V.KO, 7.0)
    w0 = cnt(4)
    fset(foe_wm, VAR(24), 99.0)
    put(me_wm, 0x0F000340 + 8 * 1 + 0, V.KO, -3.0)          # me's KO writes SLOT2_SHARED_0: foe's VAR_24
    setup(me)
    check('set-up: the unfired KO items written (2: VAR_7, the cross-object one), not the fired one again', cnt(4) - w0, 2)
    check('... foe\'s VAR_24 written by my KO (SLOT2_SHARED_0)', fget(foe_wm, VAR(24)), -3.0)
    check('... my list freed', blk(me_wm), None)
    check('... my variables cleared by the set-up as before', (fget(me_wm, VAR(6)), fget(me_wm, VAR(7))), (0.0, 0.0))
    check('set-up counter', cnt(7) >= 1, True)
    setup(foe)
    check('a set-up with no KO items: list freed, no write', blk(foe_wm), None)

    # ---- an article: no events (its status / situation never reach the fighters' hooks); its list freed at set-up
    put(art_wm, VAR(0), 15, 1.0)
    fset(art_wm, VAR(0), 9.0)
    setup(art)
    check('article: the set-up writes nothing (not a fighter), frees its list', (blk(art_wm), fget(art_wm, VAR(0))),
          (None, 0.0))

    # ---- New_Var's Reset
    state, flags, prm = MEM + 0x20000, MEM + 0x20100, MEM + 0x20200
    name = b'combo'.ljust(24, b'\0')

    def newvar(mu, handler, ident, typ, init, scope, reset=0, exe=1, acc=me):
        word = scope | (reset << 8)
        mu.mem_write(prm, struct.pack('>IIfI', ident, typ, init, word) + name)
        w32(mu, state + 4, 0x1000)
        w32(mu, state + 8, -1)
        mu.mem_write(flags + 8, bytes([exe]))
        run(mu, handler, RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: flags,
                               UC_PPC_REG_7: prm})
        return mu.reg_read(UC_PPC_REG_3), r32(mu, state + 4) - 0x1000, r32(mu, prm + 0xC)
    check('New_Var(Reset=2): returns 2, steps 44, its Scope word put back', newvar(pm, L['vr_newvar'], NV(10), 1, 3.0, 0, 2),
          (2, 44, 0x200))
    check('... Initial set, the item (Initial, landing)', (fget(me_wm, NV(10)), items(me_wm).get(NV(10))), (3.0, (3.0, 2)))
    fset(me_wm, NV(10), 8.0)
    newvar(pm, L['vr_newvar'], NV(10), 1, 3.0, 0, 2)
    check('again (Scope object): the value kept', fget(me_wm, NV(10)), 8.0)
    sit(me_sm, 2, 0)
    check('landing puts Initial back', fget(me_wm, NV(10)), 3.0)
    newvar(pm, L['vr_newvar'], NV(11), 1, 2.9, 1, 9)
    fset(me_wm, NV(11), 40.0)
    hit(me, 0)
    check('int New_Var(Initial 2.9, Reset=9): a hit -> 2', fget(me_wm, NV(11)), 2.0)
    check('Scope move with Reset: every run Initial', (newvar(pm, L['vr_newvar'], NV(11), 1, 2.9, 1, 9)[0],
                                                      fget(me_wm, NV(11))), (2, 2.0))
    newvar(pm, L['vr_newvar'], NV(10), 1, 3.0, 0, 0)
    check('New_Var with Reset 0 removes the slot\'s item', NV(10) in items(me_wm), False)
    before = snap()
    newvar(pm, L['vr_newvar'], NV(12), 0, 1.0, 0, 4, exe=0)
    check('not executed: nothing (steps)', snap() == before, True)
    newvar(pm, L['vr_newvar'], VAR(3), 0, 1.0, 0, 4)
    check('a non-New_Var ID: no item', VAR(3) in items(me_wm), False)

    # Reset 0: New_Var exactly as exe_v46v's (the same scripts on BASE's h_newvar and PATCHED's vr_newvar)
    om_me = obj(om, MEM + 0x10000)[0]
    seq = [(NV(20), 0, 1.5, 0), (NV(20), 0, 9.0, 0), (NV(21), 1, 3.9, 1), (NV(40), 1, 7.0, 0), (NV(41), 0, -1.0, 1),
           (NV(21), 0, 0.0, 0), (VAR(3), 0, 4.0, 1)]
    fresh = MEM + 0x14000
    pm_o, pm_wm, _ = obj(pm, fresh)
    om_o, om_wm, _ = obj(om, fresh)
    res_p = [newvar(pm, L['vr_newvar'], *s, acc=pm_o) for s in seq]
    res_o = [newvar(om, E['h_newvar'], *s, acc=om_o) for s in seq]
    del om_me

    def entry_bytes(mu, wm):
        for i in range(C.OBJ_N):
            e = C.OBJS + C.OBJ_SIZE * i
            if r32(mu, e) == wm:
                return bytes(mu.mem_read(e, C.OBJ_SIZE)) + bytes(mu.mem_read(e + C.NV_OFF, C.OBJ_SIZE))
        return None
    check('Reset 0: the same results as exe_v46v\'s New_Var', res_p, res_o)
    eb_p, eb_o = entry_bytes(pm, pm_wm), entry_bytes(om, om_wm)
    check('Reset 0: the object\'s variables / masks byte for byte as exe_v46v\'s', (eb_p is not None, eb_p == eb_o),
          (True, True))
    check('Reset 0: no reset list', blk(pm_wm), None)

    # ---- Var_Reset_Set(Variable, Reset, Value, Owner)
    def vrs(ident, reset, value, owner, acc=me, exe=1):
        pm.mem_write(prm, struct.pack('>IIfI', ident, reset, value, owner))
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, -1)
        pm.mem_write(flags + 8, bytes([exe]))
        run(pm, L['vr_cmd'], RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: flags,
                                   UC_PPC_REG_7: prm})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000
    check('Var_Reset_Set: returns 2, steps 20', vrs(VAR(8), V.LANDING, 0.25, 0), (2, 20))
    check('... on this object', items(me_wm).get(VAR(8)), (0.25, 2))
    vrs(VAR(24), V.HIT | V.KO, -7.0, 4)                     # Owner 4: player slot 2 = foe
    check('Owner 4 (slot 2): the item on that fighter', (items(foe_wm).get(VAR(24)), VAR(24) in items(me_wm)),
          ((-7.0, 9), False))
    fset(foe_wm, VAR(24), 1.0)
    hit(me, 0)
    check('... my hit doesn\'t reset it', fget(foe_wm, VAR(24)), 1.0)
    hit(foe, 0)
    check('... its own hit does', fget(foe_wm, VAR(24)), -7.0)
    vrs(VAR(8), 0, 0.0, 0)
    check('Reset 0 removes', VAR(8) in items(me_wm), False)
    before = snap()
    check('not executed: steps, nothing', (vrs(VAR(9), 1, 1.0, 0, exe=0), snap() == before), ((2, 20), True))
    check('a bad accessor: nothing', (vrs(VAR(9), 1, 1.0, 0, acc=0x1234), snap() == before), ((2, 20), True))
    check('ID 0: nothing', (vrs(0, 1, 1.0, 0), snap() == before), ((2, 20), True))

    # ---- MSC: the selection IDs
    fset(me_wm, 0x0F000000 | V.VAR_SEL, float(0x115 + 0x20 * 4))       # SLOT2_INPUT_OFF (target 4) as I see it
    fset(me_wm, 0x0F000000 | V.VAR_VALUE, 0.0)
    fset(me_wm, 0x0F000000 | V.VAR_OWNER, 0.0)
    fset(me_wm, 0x0F000000 | V.VAR_RESET, 1.0)
    check('MSC: selection read back', [fget(me_wm, 0x0F000000 | i) for i in (V.VAR_SEL, V.VAR_VALUE, V.VAR_OWNER, V.VAR_RESET)],
          [float(0x195), 0.0, 0.0, 1.0])
    check('MSC: the item (0x0F000195, 0, KO) on me', items(me_wm).get(0x0F000195), (0.0, 1))
    fset(me_wm, 0x0F000000 | V.VAR_SEL, float(0x115))                   # SELF_INPUT_OFF of the slot-2 fighter
    fset(me_wm, 0x0F000000 | V.VAR_OWNER, 4.0)
    fset(me_wm, 0x0F000000 | V.VAR_RESET, 9.0)
    check('MSC: owner 4: the item on foe, its own input-off', items(foe_wm).get(0x0F000115), (0.0, 9))
    check('MSC: its mask reads 9', fget(me_wm, 0x0F000000 | V.VAR_RESET), 9.0)
    fset(me_wm, 0x0F000000 | V.VAR_RESET, 0.0)
    check('MSC: 0 removes it', (0x0F000115 in items(foe_wm), fget(me_wm, 0x0F000000 | V.VAR_RESET)), (False, 0.0))
    check('0x0F0003CE and up still read 0', [fget(me_wm, 0x0F000000 | i) for i in (0x3CE, 0x3FF)], [0.0, 0.0])
    w32(pm, V.VR_DATA + V.D_BUSY, 1)
    fset(me_wm, 0x0F000000 | V.VAR_SEL, float(0x301))
    w32(pm, V.VR_DATA + V.D_BUSY, 0)
    check('MSC writes ignored while an event writes (busy)', fget(me_wm, 0x0F000000 | V.VAR_SEL), float(0x115))
    # an event whose write is a selection ID: the list isn't changed under it
    put(me_wm, 0x0F000000 | V.VAR_RESET, V.LANDING, 0.0)
    n0 = len(items(me_wm))
    sit(me_sm, 2, 0)
    check('an item writing VAR_RESET during an event: ignored (busy), the list unchanged', len(items(me_wm)), n0)
    check('busy back to 0', r32(pm, V.VR_DATA + V.D_BUSY), 0)

    # ---- the list full
    setup(foe)                                              # (its list emptied first)
    for k in range(V.VR_ITEMS):
        put(foe_wm, NV(k), V.LANDING, float(k))
    r0 = cnt(6)
    check('31 items: the 32nd refused, counted', (put(foe_wm, NV(40), V.LANDING, 1.0), cnt(6) - r0), (0, 1))
    check('... an existing one still changes', (put(foe_wm, NV(3), V.LEDGE, 9.0), items(foe_wm)[NV(3)]), (1, (9.0, 4)))
    sit(foe_sm, 2, 0)
    check('... landing writes the 30 landing ones', [fget(foe_wm, NV(k)) for k in (0, 1, 2, 30)], [0.0, 1.0, 2.0, 30.0])

    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
