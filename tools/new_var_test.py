#!/usr/bin/env python3
"""Tests New_Var (tools/acmd_ext_cave.py nv_code, docs/acmd-extra-commands.md "New_Var") in a patched RPX (unicorn).

  python3 tools/new_var_test.py PATCHED.rpx BASE.rpx

BASE is the executable it was built on (exe_v39): the hook words held what the cave expects there (obj_find's
`li r0, 0`, ue_shared's `bge ue_zero`, every WorkModule class's int ops in its vtable) and the New_Var space was past
the text region. On PATCHED:
- the words: the code, the hooks, the vtable words (and their relocations moved to the dead word), the text region;
- the command's CRC gives its index, the handler table h_newvar, size 11;
- the float path (the game's own get_float / set_float with position_vars_cave.py's hooks, every WorkModule class):
  0x0F000380 + k reads 0 unset, keeps what is written, per object, apart from VAR_n (and VAR_n apart from it), slot 63,
  any top nibble (0x1F000380 is slot 0); 0x0F0003C0-3FF still read 0 and write nothing; callee-saved registers kept;
- the int path through the WorkModule vtables (the game's own ACMD handlers SET_INT, ADD_INT, INC_INT,
  Int_Var_Compare and INT_VAR_COMPARE_VAR, and each op of each class's vtable: get, set, inc, dec, add, sub, mul, div
  (by 0: nothing), the count-down op); other int IDs go on in the game's code exactly as before (a category-0 int);
- New_Var: Scope object initialises once (a second run keeps the value), again after the object's set-up (the
  WorkModule reset hook) ; Scope move every run; Type int truncates float writes (SET_FLOAT 2.7 -> 2, Initial 3.9 ->
  3), Type float doesn't, a later New_Var can change the type; slots 32-63 (the second mask word); not executed: only
  steps; a jump pending: no step; a non-New_Var ID / a bad accessor: nothing, steps;
- the game's own interpreter and handlers running a loaded script (a Thread_Start block, run by the weapons' step
  hook): New_Var(move / object), INC_INT, ADD_INT, Int_Var_Compare + True, SET_FLOAT on the slots' IDs;
- an entry taken by another object starts with a clear New_Var block (obj_find's take clears it).
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import position_vars_cave as P  # noqa: E402
import rpx_patch as R  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_7, UC_PPC_REG_FPR1, UC_PPC_REG_LR, UC_PPC_REG_MSR)

fails = 0
MEM = 0x7E000000
FGET, FSET = 0x02F1DBE4, 0x02F1DC04              # the fighters' WorkModule get_float / set_float
SET_INT, ADD_INT, INC_INT, INT_CMP, INT_CMP_VAR = 0x02BD9D18, 0x02BD9D98, 0x02BD6E60, 0x02BE62C8, 0x02BE636C
NV = lambda k: 0x0F000380 + k                    # noqa: E731
V = lambda k: 0x0F000300 + k                     # noqa: E731


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def run(mu, start, stop, regs, count=500000):
    mu.reg_write(UC_PPC_REG_1, 0x7F00F000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
    mu.emu_start(start, stop, count=count)


def f2bits(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def call(mu, fn, r3=0, r4=0, r5=0, f1=0.0, keep=True):
    """fn(r3, r4, r5, f1) -> (r3, f1); callee-saved r14-r31 must survive"""
    mu.reg_write(UC_PPC_REG_FPR1, f2bits(f1))
    for r in range(14, 32):
        mu.reg_write(UC_PPC_REG_3 + r - 3, 0x1000 + r)
    run(mu, fn, RET, {UC_PPC_REG_3: r3, UC_PPC_REG_4: r4, UC_PPC_REG_5: r5})
    if keep:
        bad = [r for r in range(14, 32) if mu.reg_read(UC_PPC_REG_3 + r - 3) != 0x1000 + r]
        assert not bad, 'clobbered r%s (0x%08X)' % (bad, fn)
    return (mu.reg_read(UC_PPC_REG_3),
            round(struct.unpack('>d', struct.pack('>Q', mu.reg_read(UC_PPC_REG_FPR1)))[0], 4))


def interp_tests(pm, om, a, me, me_wm, fget):
    """Thread_Start(32, 9, 0){ New_Var(charge, int, 0, Scope) INC_INT(charge) INC_INT(charge) ADD_INT(5, charge)
    Int_Var_Compare(charge, ==, 7) True(5){ SET_FLOAT(1.5, power) } Script_End } Script_End, loaded (command words =
    indices), run by the weapons' step hook -> thread_run -> the game's interpreter and handlers"""
    CRC_TABLE, COUNT = 0x100FAAB8, 584
    idx = {r32(om, CRC_TABLE + 8 * i): r32(om, CRC_TABLE + 8 * i + 4) for i in range(COUNT)}
    new = {c[0]: C.NEW_BASE + k for k, c in enumerate(C.COMMANDS)}
    fb = lambda v: struct.unpack('>I', struct.pack('>f', v))[0]          # noqa: E731
    INC, ADD, ICMP, TRUE, SETF, END = 0x8827F88C, 0xA873499D, 0x477705C2, 0xA5BD4F32, 0x1E3AB92A, 0x5766F889
    script, state, ctx, table, holder = MEM + 0x30000, MEM + 0x30400, MEM + 0x30500, MEM + 0x30600, MEM + 0x30700
    name = list(struct.unpack('>6I', b'charge'.ljust(24, b'\0')))

    def load(scope, cmp_value=7):
        words = ([new['Thread_Start'], 32, 9, 0] +
                 [new['New_Var'], NV(0), 1, fb(0.0), scope] + name +
                 [idx[INC], NV(0), idx[INC], NV(0), idx[ADD], 5, NV(0), idx[ICMP], NV(0), 0, cmp_value,
                  idx[TRUE], 5, idx[SETF], fb(1.5), NV(1), idx[END], idx[END]])
        for i, w in enumerate(words):
            w32(pm, script + 4 * i, w)

    def start_and_run(scope, cmp_value=7):
        load(scope, cmp_value)
        w32(pm, state + 4, script)
        w32(pm, state + 8, -1)
        pm.mem_write(ctx + 8, b'\1')
        run(pm, a.addr('h_thread'), RET, {UC_PPC_REG_3: me, UC_PPC_REG_4: table, UC_PPC_REG_5: state,
                                          UC_PPC_REG_6: ctx, UC_PPC_REG_7: script + 4})
        jumped = r32(pm, state + 4) - script
        w32(pm, holder, me)
        run(pm, C.STEP_HOOKS[1], C.STEP_HOOKS[1] + 4, {UC_PPC_REG_3: 0x1234, UC_PPC_REG_4: holder})
        return jumped
    for lo, hi in ((0x02BEE63C, 0x02BEE9B8), (0x02BE5500, 0x02BE5B00)):     # Gekko paired-single saves: nop
        for at in range(lo, hi, 4):
            if r32(pm, at) >> 26 in (4, 56, 57, 60, 61):
                w32(pm, at, 0x60000000)
    w32(pm, me + 0x48, 0)                                  # no StopModule: not in hitlag
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 28: me})                      # a fresh object
    check('interpreter: Thread_Start jumps over the block (32 words)', start_and_run(1), 128)
    check('interpreter: New_Var(move) 0, INC_INT x2, ADD_INT 5 -> 7; Int_Var_Compare == 7 -> True: SET_FLOAT 1.5',
          (fget(me_wm, NV(0)), fget(me_wm, NV(1))), (7.0, 1.5))
    start_and_run(1, 99)
    check('interpreter: again (Scope move): 7 again; compare false (power kept at 1.5)',
          (fget(me_wm, NV(0)), fget(me_wm, NV(1))), (7.0, 1.5))
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 28: me})
    start_and_run(0)
    start_and_run(0, 14)
    check('interpreter: Scope object: the second run goes on from 7 -> 14 (compare true)',
          (fget(me_wm, NV(0)), fget(me_wm, NV(1))), (14.0, 1.5))
    check('interpreter: the thread ended (its Script_End)', any(r32(pm, C.THREADS + C.THREAD_SIZE * k) == me
                                                                for k in range(C.THREAD_N)), False)


def main():
    patched, base = sys.argv[1:3]
    a, words, hooks = C.build()
    om, pm = machine(base), machine(patched)

    # ---- words
    of_take = a.addr('of_take')
    check('base: obj_find\'s take was li r0, 0', r32(om, of_take), 0x38000000)
    check('patched: b nv_take', r32(pm, of_take), words[(of_take - C.CAVE) // 4])
    check('base: the vtables held each class\'s own int ops', {at: r32(om, at) for at in C.WM_INT_ORIG}, C.WM_INT_ORIG)
    check('patched: every vtable word -> nvi_*', {at: r32(pm, at) for at in C.WM_INT_ORIG},
          {vt + off: a.addr('nvi_' + n) for vt in C.WM_VTABLES for off, n, _b in C.WM_INT_OPS})
    check('code in place', [r32(pm, a.part4[0] + 4 * i) for i in range(len(a.part4[1]))], a.part4[1])
    check('main part in place', [r32(pm, C.CAVE + 4 * i) for i in range(len(words))], words)
    for name, path in (('base', base), ('patched', patched)):
        d, _s, _e, secs = R.load(path)
        info = R.section_data(d, next(s for s in secs if s[1] == R.SHT_RPL_FILEINFO))
        region = struct.unpack('>I', info[4:8])[0]
        text = next(s for s in secs if s[1] == 1 and s[3] == 0x02000020)
        end = text[3] + len(R.section_data(d, text))
        check('%s: text region / section end' % name, (hex(region), hex(end)),
              ('0x2bd0000', '0x4bd0000') if name == 'base' else (hex(C.NV_LIMIT - 0x02000000), hex(C.NV_LIMIT)))
        relocs = set()
        for s in secs:
            if s[1] == 4:
                rd = R.section_data(d, s)
                relocs |= {struct.unpack('>I', rd[o:o + 4])[0] for o in range(0, len(rd), 12)}
        check('%s: relocations at the vtable words' % name, len(relocs & set(C.WM_INT_ORIG)),
              len(C.WM_INT_ORIG) if name == 'base' else 0)
    crc = zlib.crc32(b'New_Var') & 0xFFFFFFFF
    k = [c[0] for c in C.COMMANDS].index('New_Var')
    run(pm, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
    check('CRC 0x%08X -> index %d' % (crc, C.NEW_BASE + k), pm.reg_read(UC_PPC_REG_3), C.NEW_BASE + k)
    check('handler table: h_newvar', r32(pm, a.addr('cmd_handlers') + 4 * k), a.addr('h_newvar'))
    check('size 11 words', (C.COMMANDS[k][1], r32(pm, a.addr('cmd_sizes') + 4 * k)), (11, 11))

    # ---- fakes: objects (accessor +0x28 WorkModule; WorkModule +0 vtable, +8 the int categories)
    pm.mem_map(MEM, 0x100000)

    def obj(base, vt=0x1013A1C0):
        acc, wm, cats, cat0, ints = base, base + 0x100, base + 0x200, base + 0x300, base + 0x400
        w32(pm, acc + 0x28, wm)
        w32(pm, wm, vt)
        w32(pm, wm + 8, cats)
        w32(pm, cats, cat0)                     # category 0: ints at +0xC
        w32(pm, cat0 + 0xC, ints)
        return acc, wm, ints
    me, me_wm, me_ints = obj(MEM + 0x10000)
    foe, foe_wm, _ = obj(MEM + 0x11000)
    state, flags, prm = MEM + 0x20000, MEM + 0x20100, MEM + 0x20200

    def fget(wm, ident, fn=FGET):
        return call(pm, fn, wm, ident)[1]

    def fset(wm, ident, v, fn=FSET):
        call(pm, fn, wm, ident, f1=v)

    def entry(wm):
        for i in range(C.OBJ_N):
            if r32(pm, C.OBJS + C.OBJ_SIZE * i) == wm:
                return C.OBJS + C.OBJ_SIZE * i
        return None

    def objs():
        return bytes(pm.mem_read(C.OBJS, C.OBJ_N * C.OBJ_SIZE)) + bytes(pm.mem_read(C.NV_POOL, C.OBJ_N * C.OBJ_SIZE))

    # ---- the float path
    check('unset New_Var slot reads 0', fget(me_wm, NV(0)), 0.0)
    check('a read creates no entry', entry(me_wm), None)
    fset(me_wm, NV(0), 7.25)
    check('set_float / get_float slot 0', fget(me_wm, NV(0)), 7.25)
    e = entry(me_wm)
    check('the value is in the entry\'s block', struct.unpack('>f', pm.mem_read(e + C.NV_OFF, 4))[0], 7.25)
    check('VAR_0 untouched by slot 0', fget(me_wm, V(0)), 0.0)
    fset(me_wm, V(0), -3.0)
    check('VAR_0 written: slot 0 unchanged', (fget(me_wm, NV(0)), fget(me_wm, V(0))), (7.25, -3.0))
    fset(me_wm, NV(63), 1.5)
    check('slot 63', fget(me_wm, NV(63)), 1.5)
    check('top nibble ignored (0x1F000380 = slot 0)', fget(me_wm, 0x1F000380), 7.25)
    check('another object: its own slots', fget(foe_wm, NV(0)), 0.0)
    fset(foe_wm, NV(0), 2.0)
    check('... kept apart', (fget(me_wm, NV(0)), fget(foe_wm, NV(0))), (7.25, 2.0))
    check('every WorkModule class\'s get_float', [fget(me_wm, NV(63), cls[0]) for cls in P.CLASSES], [1.5] * len(P.CLASSES))
    for n, cls in enumerate(P.CLASSES):
        fset(me_wm, NV(10), 20.0 + n, cls[1])
        check('set_float of class %d' % n, fget(me_wm, NV(10)), 20.0 + n)
    call(pm, 0x02F1DCF8, me_wm, NV(10), f1=1.0)          # add_float / sub_float (SUB_FLOAT_2): a read + a write
    call(pm, 0x02F1DD20, me_wm, NV(10), f1=0.5)
    check('add_float 1 / sub_float 0.5', fget(me_wm, NV(10)), 24.5)
    before = objs()
    for ident in (0x3C0, 0x3FF, 0x337, 0x33F):
        fset(me_wm, 0x0F000000 + ident, 5.0)
        check('ID 0x0F000%03X still reads 0, a write changes nothing' % ident,
              (fget(me_wm, 0x0F000000 + ident), objs() == before), (0.0, True))

    # ---- the int path (vtables)
    def acmd(handler, params, st8=-1):
        for i, p in enumerate(params):
            w32(pm, prm + 4 * i, p)
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, st8)
        w32(pm, state + 0xC, 0x55)
        pm.mem_write(flags + 8, b'\1')
        run(pm, handler, RET, {UC_PPC_REG_3: me, UC_PPC_REG_4: 0, UC_PPC_REG_5: state, UC_PPC_REG_6: flags,
                               UC_PPC_REG_7: prm})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000, r32(pm, state + 0xC)
    acmd(SET_INT, [5, NV(1)])
    check('SET_INT(5, slot 1): the float reads 5', fget(me_wm, NV(1)), 5.0)
    acmd(INC_INT, [NV(1)])
    check('INC_INT', fget(me_wm, NV(1)), 6.0)
    acmd(ADD_INT, [10, NV(1)])
    check('ADD_INT 10', fget(me_wm, NV(1)), 16.0)
    acmd(ADD_INT, [-20, NV(1)])
    check('ADD_INT -20', fget(me_wm, NV(1)), -4.0)
    check('Int_Var_Compare(slot 1 == -4): true', acmd(INT_CMP, [NV(1), 0, -4])[2], 1)
    check('Int_Var_Compare(slot 1 > 0): false', acmd(INT_CMP, [NV(1), 5, 0])[2], 0)
    fset(me_wm, NV(2), -4.9)
    check('INT_VAR_COMPARE_VAR(slot 1 == slot 2: -4.9 read as an int -4)', acmd(INT_CMP_VAR, [NV(1), 0, NV(2)])[2], 1)
    fset(me_wm, NV(3), 3.75)
    check('get_int of a float value: truncated toward 0', call(pm, a.addr('nvi_get'), me_wm, NV(3))[0], 3)
    ops = {n: a.addr('nvi_' + n) for _o, n, _b in C.WM_INT_OPS}

    def iop(name, v=None, ident=NV(4), wm=me_wm):
        if name in ('set', 'add', 'sub', 'mul', 'div'):
            return call(pm, ops[name], wm, v, ident)[0]
        return call(pm, ops[name], wm, ident, v or 0)[0]
    iop('set', 100)
    iop('dec')
    check('set 100, dec', fget(me_wm, NV(4)), 99.0)
    iop('sub', 9)
    iop('mul', -2)
    check('sub 9, mul -2', fget(me_wm, NV(4)), -180.0)
    iop('div', 7)
    check('div 7 (toward 0)', fget(me_wm, NV(4)), -25.0)
    iop('div', 0)
    check('div 0: unchanged', fget(me_wm, NV(4)), -25.0)
    iop('set', 3)
    got = [iop('cdown', 1), fget(me_wm, NV(4)), iop('cdown', 1), fget(me_wm, NV(4)), iop('cdown', 1),
           fget(me_wm, NV(4))]
    check('count-down to 1 from 3: (0, 2), (1, 1), (0, 1)', got, [0, 2.0, 1, 1.0, 0, 1.0])
    for vt in C.WM_VTABLES:
        w32(pm, me_wm, vt)
        acmd(SET_INT, [40 + (vt & 0xFF), NV(5)])
        check('class vtable 0x%08X: SET_INT, then get_int through it' % vt,
              (fget(me_wm, NV(5)), acmd(INT_CMP, [NV(5), 0, 40 + (vt & 0xFF)])[2]), (40.0 + (vt & 0xFF), 1))
    w32(pm, me_wm, 0x1013A1C0)
    # other int IDs: the game's own code (category 0 int 5 = me_ints[5]), through every class
    for n, vt in enumerate(C.WM_VTABLES):
        w32(pm, me_wm, vt)
        acmd(SET_INT, [123 + n, 0x10000005])
        acmd(INC_INT, [0x10000005])
        check('class %d: a normal int (0x10000005): SET_INT + INC_INT in its table' % n, r32(pm, me_ints + 0x14), 124 + n)
        check('class %d: Int_Var_Compare on it' % n, acmd(INT_CMP, [0x10000005, 0, 124 + n])[2], 1)
        for name in ('dec', 'add', 'sub', 'mul', 'div', 'cdown'):
            w32(pm, me_ints + 0x14, 50)
            iop(name, 5, 0x10000005)
            want = {'dec': 49, 'add': 55, 'sub': 45, 'mul': 250, 'div': 10, 'cdown': 49}[name]
            check('class %d: %s on a normal int: the game\'s result' % (n, name), r32(pm, me_ints + 0x14), want)
    w32(pm, me_wm, 0x1013A1C0)
    check('a normal int\'s get_int: the game\'s (49 after the count-down)', call(pm, ops['get'], me_wm, 0x10000005)[0], 49)
    check('slot 4 untouched by the normal int\'s ops', fget(me_wm, NV(4)), 1.0)

    # ---- New_Var
    def newvar(slot_id, typ, init, scope, exe=1, st8=-1, acc=None):
        name = b'charge'.ljust(4 * C.NV_NAME_WORDS, b'\0')
        pm.mem_write(prm, struct.pack('>IIfI', slot_id & 0xFFFFFFFF, typ, init, scope) + name)
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, st8)
        pm.mem_write(flags + 8, bytes([exe]))
        run(pm, a.addr('h_newvar'), RET, {UC_PPC_REG_3: acc or me, UC_PPC_REG_4: 0, UC_PPC_REG_5: state,
                                          UC_PPC_REG_6: flags, UC_PPC_REG_7: prm})
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000
    check('New_Var: returns 2, steps 44 bytes', newvar(NV(20), 0, 1.5, 0), (2, 44))
    check('New_Var(object): Initial 1.5', fget(me_wm, NV(20)), 1.5)
    fset(me_wm, NV(20), 9.0)
    newvar(NV(20), 0, 1.5, 0)
    check('New_Var(object) again: the value kept', fget(me_wm, NV(20)), 9.0)
    newvar(NV(20), 0, 1.5, 1)
    check('New_Var(move): Initial again', fget(me_wm, NV(20)), 1.5)
    fset(me_wm, NV(20), 9.0)
    newvar(NV(20), 0, 1.5, 1)
    check('New_Var(move) every run', fget(me_wm, NV(20)), 1.5)
    newvar(NV(21), 1, 3.9, 0)
    check('New_Var(int, Initial 3.9): 3', fget(me_wm, NV(21)), 3.0)
    fset(me_wm, NV(21), 2.7)
    check('int: SET_FLOAT 2.7 -> 2', fget(me_wm, NV(21)), 2.0)
    fset(me_wm, NV(21), -2.7)
    check('int: -2.7 -> -2', fget(me_wm, NV(21)), -2.0)
    fset(me_wm, NV(20), 2.7)
    check('float: 2.7 kept', fget(me_wm, NV(20)), 2.7)
    newvar(NV(21), 0, 0, 0)
    fset(me_wm, NV(21), 2.7)
    check('a later New_Var(float) makes it float (declared already: value kept)', fget(me_wm, NV(21)), 2.7)
    newvar(NV(40), 1, 7.0, 0)
    newvar(NV(41), 0, -1.0, 0)
    e = entry(me_wm)
    check('slots 40 / 41 (second mask word)', (fget(me_wm, NV(40)), fget(me_wm, NV(41))), (7.0, -1.0))
    check('masks: declared / int', (r32(pm, e + C.NV_DECL), r32(pm, e + C.NV_DECL + 4), r32(pm, e + C.NV_INT),
                                    r32(pm, e + C.NV_INT + 4)), (3 << 20, 3 << 8, 0, 1 << 8))
    fset(me_wm, NV(40), 5.5)
    check('slot 40 int: 5.5 -> 5', fget(me_wm, NV(40)), 5.0)
    snap = objs()
    check('not executed: steps only', (newvar(NV(30), 0, 4.0, 1, exe=0), objs() == snap), ((2, 44), True))
    check('a jump pending: no step', newvar(NV(30), 0, 4.0, 1, st8=5)[1], 0)
    snap = objs()
    for bad in (V(3), 0x0F0003C0, 0x0F000300 | 0x7F, 0x0E000380):
        check('a non-New_Var ID 0x%08X: nothing, steps' % bad, (newvar(bad, 0, 4.0, 1), objs() == snap), ((2, 44), True))
    check('a bad accessor: nothing, steps', (newvar(NV(30), 0, 4.0, 1, acc=0x1234), objs() == snap), ((2, 44), True))
    w32(pm, MEM + 0x12000 + 0x28, 0)
    check('no WorkModule: nothing, steps', (newvar(NV(30), 0, 4.0, 1, acc=MEM + 0x12000), objs() == snap),
          ((2, 44), True))
    newvar(NV(31), 0, 6.0, 0, st8=5)
    check('a jump pending but executed: still declares', fget(me_wm, NV(31)), 6.0)

    # the object set up again (WorkModule reset hook): forgotten; the next New_Var(object) initialises again
    run(pm, C.WM_RESET, C.WM_RESET + 4, {UC_PPC_REG_3 + 28: me})
    check('set-up: the slots read 0', (fget(me_wm, NV(20)), fget(me_wm, NV(40))), (0.0, 0.0))
    newvar(NV(20), 0, 1.5, 0)
    check('set-up: New_Var(object) initialises again', fget(me_wm, NV(20)), 1.5)
    check('... the others start at 0, float', (fget(me_wm, NV(21)), fget(me_wm, NV(40))), (0.0, 0.0))
    fset(me_wm, NV(40), 5.5)
    check('... slot 40 is float again', fget(me_wm, NV(40)), 5.5)

    # the game's own interpreter running a script (a thread block, so the step hook runs it as in game) with
    # New_Var and the vanilla int / float commands on the names' IDs, as Sm4shCommand compiles them
    interp_tests(pm, om, a, me, me_wm, fget)

    # an entry reused by another object: its New_Var block is cleared (fill every entry, then one more object)
    for i in range(C.OBJ_N):
        if r32(pm, C.OBJS + C.OBJ_SIZE * i) == 0:
            w32(pm, C.OBJS + C.OBJ_SIZE * i, MEM + 0x50000 + 0x100 * i)
    for i in range(C.OBJ_N):
        pm.mem_write(C.NV_POOL + C.OBJ_SIZE * i, b'\x41' * C.OBJ_SIZE)
    new_wm = obj(MEM + 0x13000)[1]
    fset(new_wm, NV(7), 1.0)
    e = entry(new_wm)
    blk = bytes(pm.mem_read(e + C.NV_OFF, C.OBJ_SIZE))
    check('a taken entry: its block cleared (but the value written)', (blk[:28], blk[32:], fget(new_wm, NV(7))),
          (b'\0' * 28, b'\0' * (C.OBJ_SIZE - 32), 1.0))
    check('... and its masks', [r32(pm, e + o) for o in (C.NV_DECL, C.NV_DECL + 4, C.NV_INT, C.NV_INT + 4)], [0] * 4)

    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
