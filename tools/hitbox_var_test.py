#!/usr/bin/env python3
"""Tests the Extra hitbox commands' variables (tools/acmd_ext_cave.py hv_code, exe_v43; docs/acmd-extra-commands.md
"Variables in Extra hitboxes") in unicorn.

  python3 tools/hitbox_var_test.py PATCHED.rpx BASE.rpx     the executables (BASE: exe_v42, what v43 is built on)
  python3 tools/hitbox_var_test.py --synthetic              the cave alone (its words from acmd_ext_cave.py)

PATCHED / BASE: the word diff BASE -> PATCHED is exactly the cave's own change (the HV_CODE words, the two
Extra handler table words, gv_zero, the FRAME_HOOK / WM_RESET hook words), the replaced words held what v42 had; then
every test below runs on PATCHED's code, the Extra hitboxes through the game's own hitbox handlers (Special_Hitbox
0x02BDBB20, Extended_Special_Hitbox 0x02BDD46C) and AttackModule's set_attack (0x02C086A8, the real class: vtable
0x10103524), with the fighter's other modules as stubs that return 0 (every call logged), and the slot each builds
from variables is compared byte for byte with the slot BASE builds from the same values written as numbers.
--synthetic: the base handlers are a stub that builds the slot data from the parameters as the game's do (+0x18
Damage (x1.15 for a "Strike" flag, to test the FOLLOW ratio), +0x1C Size, +0x20 Angle, +0x24 KBG, +0x28 FKB, +0x2C
BKB) and clears the tag (as the slot_set hook does), the WorkModule's get_float / get_int a table (the mod's
0x0F0003xx IDs go to the cave's user_entry, as position_vars' hooks send them), PostureModuleF a table (facing,
rotation). Both:
- old scripts: a command without variables does exactly what h_extra did (the same slot, extras entry, script words,
  step), executed or skipped;
- each field from a variable (float VAR_n, New_Var int / float, a game int 0x1000xxxx through get_int): Damage /
  Size >= 0, KBG / FKB / BKB rounded (halves away from 0) and >= 0, Angle rounded, 361-368 kept, else wrapped into
  0-359 (-30 -> 330, 725 -> 5, 359.6 -> 0, 360 -> 0, -0.5 -> 359); NEG; WORLD (facing left: 180 - a); the command's
  words are put back after it ran; skipped: nothing read;
- STICK_ANGLE / STICK_ANGLE_RAW / STICK_LEN and the C-stick's (0x0F0003C0-3C5) against math.atan2 / hypot, (0, 0)
  -> 0; ROT_X / Y / Z (0x3C6-3C8) = PostureModuleF(4-6); writes ignored; 0x3C9+ and 0x339-0x33F still read 0;
- the user's examples: a hitbox at the stick's angle (STICK_ANGLE, and STICK_ANGLE_RAW|WORLD giving the same angle
  facing either way); Rotation_Get(Target=0, Axis=0, Variable=VAR_1) then Angle=VAR_1 (and ROT_X|NEG);
- FOLLOW: every frame (FRAME_HOOK, through hk_frame) the fields are read again (Damage x the ratio the game's path
  gave, Angle in the extras' check words: ext_find still finds the extras), a later hitbox in the slot (plain or
  Extra) or the object's reset (WM_RESET) ends it, other objects' frames don't touch it, 17 FOLLOW hitboxes: the
  oldest goes.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_7, UC_PPC_REG_31, UC_PPC_REG_FPR1, UC_PPC_REG_LR,
                               UC_PPC_REG_MSR, UC_PPC_REG_PC)

RET = 0x01000000
fails = 0
OBJ = 0x7E100000                 # fake objects (a block of their own, clear of the executable's data)
ACC, WM, AM, SLOTS, STATE, FLAG, SCRIPT, WMVT, MM = (OBJ + o for o in (0, 0x400, 0x800, 0x1000, 0x2000, 0x2100,
                                                                       0x2200, 0x2400, 0x2500))
ACC2, WM2, AM2, SLOTS2 = (OBJ + o for o in (0x3000, 0x3400, 0x3800, 0x4000))
STUB_GETF, STUB_GETI, STUB_SETF, STUB_ZERO = 0x7F0F0000, 0x7F0F0010, 0x7F0F0020, 0x7F0F0030
FAKEMOD, FAKEVT = 0x7F0F8000, 0x7F0F9000
AM_CTOR = 0x02C077F4             # AttackModuleImpl's constructor (this, accessor)
GROUP_CTOR = 0x02C10478          # a Part's (hit group's, 0x174 bytes) constructor (this)
HIT_GROUP = 0x02C108C4           # set_attack's hit record set-up for the slot (from the game's record pool): a stub
GROUPS, GROUPS2 = OBJ + 0x6000, OBJ + 0xA000
RECS = 0x7E200000                # hit records (rpx mode)
OBJ_OF = 0x0347B1B8              # the hitbox handlers' battle object lookup (accessor +0: its object ID)
SID = 3
VAR = lambda k: 0x0F000300 + k   # noqa: E731
FOLLOW, WORLD, NEG = (C.HV_FLAGS[k] for k in ('FOLLOW', 'WORLD', 'NEG'))
NAMES = {n: 0x0F000000 + C.HV_VARS + i for i, n in enumerate(C.HV_VAR_NAMES)}


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def near(what, got, want, eps=0.01):
    global fails
    ok = got is not None and abs(got - want) <= eps
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def w32(mu, a, v):
    mu.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))


def rf(mu, a):
    return struct.unpack('>f', mu.mem_read(a, 4))[0]


def fbits(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def bitsf(w):
    return struct.unpack('>f', struct.pack('>I', w & 0xFFFFFFFF))[0]


def f2d(v):
    return struct.unpack('>Q', struct.pack('>d', v))[0]


def d2f(q):
    return struct.unpack('>d', struct.pack('>Q', q))[0]


class World:
    """the fake fighter: its variables, sticks, facing, rotation; the stubs read them"""
    def __init__(self, mu, a, synthetic):
        self.mu, self.a, self.synthetic = mu, a, synthetic
        self.floats, self.ints = {}, {}
        self.facing, self.rot = 1.0, [0.0, 0.0, 0.0]
        self.strike = 1.0
        self.calls = []

    def ret(self, r3=None, f1=None):
        mu = self.mu
        if r3 is not None:
            mu.reg_write(UC_PPC_REG_3, r3 & 0xFFFFFFFF)
        if f1 is not None:
            mu.reg_write(UC_PPC_REG_FPR1, f2d(f1))
        mu.reg_write(UC_PPC_REG_PC, mu.reg_read(UC_PPC_REG_LR))

    def get_float(self, mu, *_):
        ident = mu.reg_read(UC_PPC_REG_4)
        if ident >> 24 == 0x0F and (ident & 0x3FF) >= C.USER_BASE:      # position_vars' hooks: var_entry, user_gate
            mu.reg_write(UC_PPC_REG_5, 0)
            mu.reg_write(UC_PPC_REG_PC, self.a.addr('user_entry'))
            return
        self.calls.append(('get_float', ident))
        self.ret(f1=self.floats.get(ident & 0x0FFFFFFF, 0.0))

    def set_float(self, mu, *_):
        ident = mu.reg_read(UC_PPC_REG_4)
        if ident >> 24 == 0x0F and (ident & 0x3FF) >= C.USER_BASE:
            mu.reg_write(UC_PPC_REG_5, 1)
            mu.reg_write(UC_PPC_REG_PC, self.a.addr('user_entry'))
            return
        self.floats[ident & 0x0FFFFFFF] = d2f(mu.reg_read(UC_PPC_REG_FPR1))
        self.ret()

    def zero(self, mu, *_):
        self.calls.append(('zero', mu.reg_read(UC_PPC_REG_LR)))
        self.ret(r3=0, f1=0.0)

    def get_int(self, mu, *_):
        ident = mu.reg_read(UC_PPC_REG_4)
        self.calls.append(('get_int', ident))
        self.ret(r3=self.ints.get(ident, 0))

    def posture(self, mu, *_):
        args = r32(mu, mu.reg_read(UC_PPC_REG_4))
        op = r32(mu, args)
        v = self.facing if op == 0 else self.rot[op - 4] if 4 <= op <= 6 else 0.0
        self.calls.append(('posture', op))
        self.ret(r3=fbits(v), f1=v)

    def base_handler(self, nbase):
        """synthetic Special_Hitbox / Extended_Special_Hitbox: the slot's data from the parameters, step"""
        def h(mu, *_):
            p, st = mu.reg_read(UC_PPC_REG_7), mu.reg_read(UC_PPC_REG_5)
            ex = mu.mem_read(mu.reg_read(UC_PPC_REG_6) + 8, 1)[0]
            if ex:
                ident = r32(mu, p)
                am = r32(mu, mu.reg_read(UC_PPC_REG_3) + 0x50)
                if ident < r32(mu, am + 0x3C):
                    slot = r32(mu, am + 0x40) + 0x84 * ident
                    words = [r32(mu, p + 4 * k) for k in range(nbase - 1)]
                    data = bytearray(0x68)
                    struct.pack_into('>ff', data, 0x18, bitsf(words[3]) * self.strike, bitsf(words[8]))
                    struct.pack_into('>IIII', data, 0x20, words[4], words[5], words[6], words[7])
                    struct.pack_into('>I', data, 0x3C, words[2])
                    struct.pack_into('>fff', data, 0x00, bitsf(words[9]), bitsf(words[10]), bitsf(words[11]))
                    mu.mem_write(slot, bytes(data))                         # (the tag +0x66: 0, as slot_set)
                    self.calls.append(('hitbox', ident))
            if r32(mu, st + 8) == 0xFFFFFFFF:
                w32(mu, st + 4, r32(mu, st + 4) + 4 * nbase)
            self.ret(r3=2)
        return h


def stub(mu, at, fn):
    mu.mem_write(at, struct.pack('>I', 0x4E800020))
    mu.hook_add(UC_HOOK_CODE, fn, begin=at, end=at)


def synthetic_machine(a, words, hooks):
    mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    mu.mem_map(0x02000000, 0x02C00000)
    mu.mem_map(OBJ, 0x10000)
    mu.mem_map(RET, 0x1000)
    mu.mem_write(RET, struct.pack('>I', 0x48000000))
    mu.mem_map(0x7F000000, 0x00100000)
    for base, ws in [(C.CAVE, words), a.part2, a.part3, a.part4, a.part5, a.part6]:
        mu.mem_write(base, b''.join(struct.pack('>I', w) for w in ws))
    for at, w in hooks.items():
        if at < 0x10000000:
            w32(mu, at, w)
    return mu


def rpx_machine(path):
    from stage_slot_test import machine
    mu = machine(path)
    taken = [(lo, hi) for lo, hi, _p in mu.mem_regions()]
    for page in range(0x10000000, 0x11000000, 0x1000):        # .bss (machine() maps the file's sections only)
        if not any(lo <= page <= hi for lo, hi in taken):
            mu.mem_map(page, 0x1000)
    mu.mem_map(OBJ, 0x10000)
    mu.mem_map(RECS, 0x10000)
    mu.mem_map(0x7F010000, 0x000F0000)
    return mu


def setup(mu, w, synthetic):
    """the fake fighter (ACC) and a second object (ACC2); stubs"""
    mu.mem_write(OBJ, b'\0' * 0x10000)
    for acc, wm, am, slots, groups in ((ACC, WM, AM, SLOTS, GROUPS), (ACC2, WM2, AM2, SLOTS2, GROUPS2)):
        w32(mu, acc + 0x28, wm)
        w32(mu, acc + 0x50, am)
        w32(mu, wm, WMVT)
        if not synthetic:                       # the game's AttackModuleImpl, made by its own constructor
            run(mu, AM_CTOR, RET, {UC_PPC_REG_3: am, UC_PPC_REG_4: acc})
            for vec, base in ((0x10, groups), (0x34, groups + 0x2000)):   # its two part arrays ({count, 20 parts
                w32(mu, am + vec, 20)                                     # of 0x174}: the game's set-up allocates
                w32(mu, am + vec + 4, base)                               # them), each made by the parts' own
                for k in range(20):                                       # constructor
                    run(mu, GROUP_CTOR, RET, {UC_PPC_REG_3: base + 0x174 * k})
        w32(mu, am + 4, acc)
        w32(mu, am + 0x3C, 10)
        w32(mu, am + 0x40, slots)
    if not synthetic:                           # the fighter's other modules: every vtable entry returns 0
        w32(mu, FAKEVT - 4, 0)
        for i in range(0x200):
            w32(mu, FAKEVT + 4 * i, STUB_ZERO)
        for i in range(0x40):                   # the WorkModule's other entries too (get_float / set_float / get_int below)
            w32(mu, WMVT + 4 * i, STUB_ZERO)
        for acc in (ACC, ACC2):
            for off in range(0, 0x200, 4):
                if off not in (0x28, 0x50):
                    w32(mu, acc + off, FAKEMOD)
            w32(mu, acc, 0xF0000000)            # its object ID: no manager has it (the game's lookups find none)
        w32(mu, FAKEMOD, FAKEVT)
        stub(mu, STUB_ZERO, w.zero)
        def hit_group(mu, *_):              # the slot's record in its Part (the game takes it from a pool its set-up
            g, ident = mu.reg_read(UC_PPC_REG_3), mu.reg_read(UC_PPC_REG_5)      # makes): a zeroed one of ours
            rec = RECS + 0x100 * ((g - OBJ) // 0x174 % 16) + 0x10 * 0 + 0x1000 * (ident % 10)
            mu.mem_write(rec, b'\0' * 0x80)
            w32(mu, g + 0x18 + 4 * ident, rec)
            w.ret(r3=0)
        stub(mu, HIT_GROUP, hit_group)
        stub(mu, OBJ_OF, lambda mu, *_: w.ret(r3=FAKEMOD))   # the battle object of the accessor (its vt +0x1CC,
                                                            # called with the data before set_attack: a stub)
    w32(mu, WMVT + 0x44, STUB_GETF)
    w32(mu, WMVT + 0x84, STUB_GETI)
    w32(mu, WMVT + 0x4C, STUB_SETF)
    w32(mu, MM + 4, ACC)
    stub(mu, STUB_GETF, w.get_float)
    stub(mu, STUB_GETI, w.get_int)
    stub(mu, STUB_SETF, w.set_float)
    stub(mu, C.POSTURE_FW, w.posture)
    if synthetic:
        stub(mu, C.SPECIAL_HITBOX, w.base_handler(42))
        stub(mu, C.EXT_SPECIAL_HITBOX, w.base_handler(44))
    for k, (wm, acc) in enumerate(((WM, ACC), (WM2, ACC2))):      # acc_of's cache (hk_frame fills it in game)
        w32(mu, C.ACC_CACHE + 8 * k, wm)
        w32(mu, C.ACC_CACHE + 8 * k + 4, acc)


def run(mu, start, stop, regs, count=400000):
    mu.reg_write(UC_PPC_REG_1, 0x7F0EF000)
    for r, v in regs.items():
        mu.reg_write(r, v & 0xFFFFFFFF)
    mu.reg_write(UC_PPC_REG_LR, RET)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # FP on
    try:
        mu.emu_start(start, stop, count=count)
    except Exception as e:                      # (the game's code reaching something the fake fighter lacks)
        sys.stderr.write('emulation stopped at pc 0x%08X (lr 0x%08X, r3 0x%08X) from 0x%08X: %s\n' % (
            mu.reg_read(UC_PPC_REG_PC), mu.reg_read(UC_PPC_REG_LR), mu.reg_read(UC_PPC_REG_3), start, e))
        raise


BASE_FIELDS = dict(ID=SID, Part=0, Bone=0, Damage=10.0, Angle=45, KBG=100, FKB=0, BKB=30, Size=4.0, X=0.0, Y=8.0,
                   Z=6.0)
FLOATS = {'Damage', 'Size', 'X', 'Y', 'Z', 'Trip', 'Hitlag', 'SDI'}


def script_words(cmd, fields, extras=(1.0, 1.0, 0, 1.0, 0, 1.0)):
    """the command's parameter words: Special_Hitbox's 41 / 43 then the 6 extras; a field given as an int bigger
    than 0xFFFFFF is a word as it is (a variable)"""
    import json
    info = json.load(open(os.path.join(HERE, 'acmd_info.json')))['commands']['%08X' % C.BASE_CRC[cmd]]
    out = []
    for name, t in zip(info['syntax'], info['format']):
        v = fields.get(name, BASE_FIELDS.get(name, 1.0 if name in ('Hitlag', 'SDI') else 0))
        if isinstance(v, int) and abs(v) > 0xFFFFFF:
            out.append(v & 0xFFFFFFFF)
        elif t == 1:
            out.append(fbits(float(v)))
        else:
            out.append(int(v) & 0xFFFFFFFF)
    for k, v in enumerate(extras):
        out.append(fbits(v) if C.EXTRA_PARAMS[k][1] == 1 else v & 0xFFFFFFFF)
    return out


def hitbox(mu, a, cmd, fields, exe=1, label=None, acc=ACC):
    """runs the command's handler (cmd_handlers': hv_extra) on a script; -> the parameter words after, the step"""
    ws = script_words(cmd, fields)
    mu.mem_write(SCRIPT, b''.join(struct.pack('>I', x) for x in ws))
    w32(mu, STATE + 4, 0x1000)
    w32(mu, STATE + 8, -1)
    mu.mem_write(FLAG + 8, bytes([exe]))
    label = label or ('hv_extra' if cmd == 'Extra_Special_Hitbox' else 'hv_extra_ext')
    run(mu, a.addr(label), RET, {UC_PPC_REG_3: acc, UC_PPC_REG_4: 0, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                 UC_PPC_REG_7: SCRIPT})
    after = [r32(mu, SCRIPT + 4 * i) for i in range(len(ws))]
    return ws, after, r32(mu, STATE + 4) - 0x1000, mu.reg_read(UC_PPC_REG_3)


def slot_of(mu, slots=SLOTS, ident=SID):
    return slots + 0x84 * ident


def slot_vals(mu, slots=SLOTS, ident=SID):
    s = slot_of(mu, slots, ident)
    d, sz = struct.unpack('>ff', mu.mem_read(s + 0x18, 8))
    ang, kbg, fkb, bkb = struct.unpack('>iiii', mu.mem_read(s + 0x20, 16))
    return round(d, 4), ang, kbg, fkb, bkb, round(sz, 4)


def ext_find(mu, a, data):
    run(mu, a.addr('ext_find'), RET, {UC_PPC_REG_3: data})
    return mu.reg_read(UC_PPC_REG_3)


def user_var(mu, a, ident, write=None):
    """the variable through the WorkModule's get_float (stub -> user_entry); write: user_entry's write path"""
    if write is None:
        run(mu, STUB_GETF, RET, {UC_PPC_REG_3: WM, UC_PPC_REG_4: ident})
    else:
        mu.reg_write(UC_PPC_REG_FPR1, f2d(write))
        run(mu, a.addr('user_entry'), RET, {UC_PPC_REG_3: WM, UC_PPC_REG_4: ident, UC_PPC_REG_5: 1})
    return round(d2f(mu.reg_read(UC_PPC_REG_FPR1)), 4)


def setv(mu, a, w, values):
    """set variables: the mod's user IDs (0x0F000300+) in the cave (user_entry's write), the rest in the stubs' table"""
    for ident, v in values.items():
        if ident >> 24 == 0x0F and (ident & 0x3FF) >= C.USER_BASE:
            user_var(mu, a, ident, write=v)
        else:
            w.floats[ident] = v


def frame(mu, a, acc=ACC):
    """the per-frame hook (FRAME_HOOK: hv_fhook -> hv_frame -> hk_frame), as the game's motion step after ACMD"""
    w32(mu, MM + 4, acc)
    run(mu, C.FRAME_HOOK, C.FRAME_HOOK + 4, {UC_PPC_REG_31: MM})


def tests(mu, a, w, ref=None):
    E = 'Extra_Special_Hitbox'
    X = 'Extra_Extended_Special_Hitbox'
    mu.mem_write(C.HV_TAB, b'\0' * (C.HV_N * C.HV_ENTRY))

    # --- old scripts: no variables -> exactly h_extra's work (slot, extras entry, words, step, return)
    for cmd in (E, X):
        for exe in (1, 0):
            snaps = []
            for label in ('h_extra' if cmd == E else 'h_extra_ext', None):
                mu.mem_write(SLOTS, b'\0' * 0x600)
                mu.mem_write(C.TABLE, b'\0' * (C.ENTRIES * C.ENTRY))
                w32(mu, a.addr('next_entry'), 0)
                mu.mem_write(C.DBG, b'\0' * 0x100)
                ws, after, step, ret = hitbox(mu, a, cmd, dict(Damage=12.0, Angle=361, KBG=90, BKB=50), exe, label)
                snaps.append((bytes(mu.mem_read(SLOTS, 0x600)), bytes(mu.mem_read(C.TABLE, C.ENTRIES * C.ENTRY)),
                              bytes(mu.mem_read(C.DBG, 0x100)), after == ws, step, ret))
            check('%s, numbers only (%s): the same as h_extra (slot, extras, counters, words, step, return)' % (
                cmd, 'run' if exe else 'skipped'), snaps[1], snaps[0])
            check('%s, numbers only: no FOLLOW entry' % cmd, bytes(mu.mem_read(C.HV_TAB, C.HV_N * C.HV_ENTRY)),
                  b'\0' * (C.HV_N * C.HV_ENTRY))

    # --- each field from a variable
    setv(mu, a, w, {0x0F000300: 12.5, 0x0F000301: 45.4, 0x0F000302: 70.5, 0x0F000303: -3.0, 0x0F000304: 0.5,
                     0x0F000305: 6.25})
    for cmd in (E, X):
        ws, after, step, ret = hitbox(mu, a, cmd, dict(Damage=VAR(0), Angle=VAR(1), KBG=VAR(2), FKB=VAR(3),
                                                       BKB=VAR(4), Size=VAR(5)))
        check('%s: all six from VAR_0-5' % cmd, slot_vals(mu), (12.5, 45, 71, 0, 1, 6.25))
        if ref:
            got = bytearray(mu.mem_read(slot_of(mu), 0x68))
            want = bytearray(ref(cmd, dict(Damage=12.5, Angle=45, KBG=71, FKB=0, BKB=1, Size=6.25)))
            got[C.TAG_OFF:C.TAG_OFF + 2] = want[C.TAG_OFF:C.TAG_OFF + 2] = b'\0\0'
            check('%s: the slot (0x68 bytes, the tag aside) = what BASE\'s game code builds from those numbers' % cmd,
                  bytes(got), bytes(want))
        check('%s: the command\'s words put back, step, return' % cmd, (after == ws, step, ret),
              (True, 4 * C.COMMANDS[0 if cmd == E else 1][1], 2))
        check('%s: the extras found from the slot' % cmd, ext_find(mu, a, slot_of(mu)) != 0, True)
    w.calls[:] = []
    ws, after, step, ret = hitbox(mu, a, E, dict(Damage=VAR(0), Angle=VAR(1)), exe=0)
    check('skipped: nothing read, words as they were', ([c for c in w.calls if c[0] != 'hitbox'], after == ws),
          ([], True))

    def angle(v, flags=0, facing=1.0):
        setv(mu, a, w, {0x0F000306: v})
        w.facing = facing
        hitbox(mu, a, E, dict(Angle=VAR(6) | flags))
        w.facing = 1.0
        return slot_vals(mu)[1]
    for v, want in [(-30, 330), (725, 5), (359.6, 0), (360, 0), (361, 361), (365, 365), (368, 368), (369, 9),
                    (-0.5, 359), (0.5, 1), (0.49, 0), (90, 90), (-725, 355), (1e9, int(1e9) % 360)]:
        check('Angle from %r -> %d' % (v, want), angle(v), want)
    check('Angle NaN -> 0..359 (no crash)', 0 <= angle(float('nan')) < 360 or angle(float('nan')) == 361, True)
    check('NEG: 30 -> 330', angle(30, NEG), 330)
    check('WORLD facing right: 30 -> 30', angle(30, WORLD, 1.0), 30)
    check('WORLD facing left: 30 -> 150', angle(30, WORLD, -1.0), 150)
    check('WORLD facing left: 200 -> 340', angle(200, WORLD, -1.0), 340)
    check('NEG + WORLD facing left: 30 -> 210', angle(30, NEG | WORLD, -1.0), 210)
    check('no WORLD, facing left: 30 stays 30 (the hitbox angle is already along the facing)', angle(30, 0, -1.0), 30)

    def num(field, v, flags=0):
        setv(mu, a, w, {0x0F000307: v})
        hitbox(mu, a, E, {field: VAR(7) | flags})
        return slot_vals(mu)[('Damage', 'Angle', 'KBG', 'FKB', 'BKB', 'Size').index(field)]
    for field, v, want in [('Damage', -4.0, 0.0), ('Damage', 7.3, 7.3), ('Size', -1.0, 0.0), ('Size', 2.5, 2.5),
                           ('KBG', -10.0, 0), ('KBG', 70.5, 71), ('KBG', 70.49, 70), ('BKB', 120.0, 120),
                           ('FKB', 0.5, 1), ('Damage', 5.0, 0.0)]:
        if (field, v) == ('Damage', 5.0):
            check('Damage 5 with NEG -> -5 -> 0', num(field, v, NEG), want)
        else:
            check('%s from %r -> %r' % (field, v, want), num(field, v), want)
    w.ints[0x10000005] = 77
    hitbox(mu, a, E, dict(KBG=0x10000005))
    check('KBG from a game int (0x10000005, get_int)', slot_vals(mu)[2], 77)
    w.ints[0x1F000385] = 33                     # New_Var int (the WorkModule's int op: nvi_get in game)
    hitbox(mu, a, E, dict(BKB=0x1F000385))
    check('BKB from an int-typed ID (0x1F000385, get_int)', slot_vals(mu)[4], 33)
    w.floats[0x0300011A] = 18.0                 # a fighter_param float
    hitbox(mu, a, E, dict(Damage=0x0300011A))
    check('Damage from a fighter_param float (0x0300011A)', slot_vals(mu)[0], 18.0)
    hitbox(mu, a, E, dict(Damage=fbits(1e-20)))     # below the range: a number (tiny)
    check('a float below 0x01000000 bits is a number', slot_vals(mu)[0], 0.0)
    hitbox(mu, a, E, dict(Angle=0x20000005))        # a flag ID: not a variable (a number, as before)
    check('a word >= 0x20000000 is a number, as before', slot_vals(mu)[1], 0x20000005)

    # --- the variables 0x0F0003C0-3C8
    for (x, y) in [(0.5, 0.5), (-1.0, 0.0), (0.0, -1.0), (0.0, 0.0), (0.3, -0.7), (-0.6, 0.8), (0.001, -0.0001),
                   (-0.9, -0.2), (1.0, 0.0), (0.0, 1.0)]:
        setv(mu, a, w, {0x0F000110: x, 0x0F000111: y, 0x0F000260: -x})      # facing left: raw x = -x
        want = math.degrees(math.atan2(y, x)) % 360 if (x, y) != (0.0, 0.0) else 0.0
        near('STICK_ANGLE (%g, %g) = %.2f' % (x, y, want), user_var(mu, a, NAMES['STICK_ANGLE']), want if want < 359.995 else 0.0)
        want_raw = math.degrees(math.atan2(y, -x)) % 360 if (x, y) != (0.0, 0.0) else 0.0
        near('STICK_ANGLE_RAW (%g, %g)' % (-x, y), user_var(mu, a, NAMES['STICK_ANGLE_RAW']), want_raw)
        near('STICK_LEN', user_var(mu, a, NAMES['STICK_LEN']), math.hypot(x, y), 1e-4)
    setv(mu, a, w, {0x0F000112: 0.0, 0x0F000113: 1.0, 0x0F000261: 0.0})
    near('CSTICK_ANGLE up = 90', user_var(mu, a, NAMES['CSTICK_ANGLE']), 90.0)
    near('CSTICK_ANGLE_RAW up = 90', user_var(mu, a, NAMES['CSTICK_ANGLE_RAW']), 90.0)
    near('CSTICK_LEN', user_var(mu, a, NAMES['CSTICK_LEN']), 1.0, 1e-4)
    w.rot = [30.0, -12.5, 200.0]
    for k, n in enumerate(('ROT_X', 'ROT_Y', 'ROT_Z')):
        check('%s = PostureModuleF(%d)' % (n, 4 + k), user_var(mu, a, NAMES[n]), w.rot[k])
    setv(mu, a, w, {0x0F000110: 0.0, 0x0F000111: 1.0})
    user_var(mu, a, NAMES['STICK_ANGLE'], write=5.0)
    near('a write to STICK_ANGLE is ignored (it still reads the stick: 90)', user_var(mu, a, NAMES['STICK_ANGLE']), 90.0)
    check('0x0F0003C9 reads 0', user_var(mu, a, 0x0F0003C9), 0.0)
    check('0x0F000339 reads 0', user_var(mu, a, 0x0F000339), 0.0)
    check('0x0F0003FF reads 0', user_var(mu, a, 0x0F0003FF), 0.0)

    # --- the user's examples
    # 1: Extra_Special_Hitbox(..., Angle=STICK_ANGLE, ...): the hitbox flies the way the stick points
    for facing, xf, y in [(1.0, 0.7, 0.7), (-1.0, 0.7, 0.7), (1.0, -1.0, 0.0), (-1.0, 0.0, -1.0)]:
        w.facing = facing
        setv(mu, a, w, {0x0F000110: xf, 0x0F000111: y, 0x0F000260: xf * facing})
        hitbox(mu, a, E, dict(Angle=NAMES['STICK_ANGLE']))
        a1 = slot_vals(mu)[1]
        hitbox(mu, a, E, dict(Angle=NAMES['STICK_ANGLE_RAW'] | WORLD))
        a2 = slot_vals(mu)[1]
        want = round(math.degrees(math.atan2(y, xf))) % 360
        check('example 1 (facing %+d, stick fwd %g / up %g): Angle=STICK_ANGLE = %d, STICK_ANGLE_RAW|WORLD the same'
              % (facing, xf, y, want), (a1, a2), (want, want))
    w.facing = 1.0
    # 2: Rotation_Get(Target=0, Axis=0, Variable=VAR_1) then Extra_Special_Hitbox(..., Angle=VAR_1, ...)
    w.rot = [30.0, 0.0, 0.0]
    p = 0x7F0F1000
    for i, x in enumerate((0, 0, VAR(1))):
        w32(mu, p + 4 * i, x)
    w32(mu, STATE + 4, 0x1000)
    w32(mu, STATE + 8, -1)
    mu.mem_write(FLAG + 8, b'\1')
    run(mu, a.addr('h_rget'), RET, {UC_PPC_REG_3: ACC, UC_PPC_REG_4: 0, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                    UC_PPC_REG_7: p})
    check('example 2: VAR_1 = 30', user_var(mu, a, VAR(1)), 30.0)
    hitbox(mu, a, E, dict(Angle=VAR(1)))
    check('example 2: Angle=VAR_1 -> 30', slot_vals(mu)[1], 30)
    hitbox(mu, a, E, dict(Angle=NAMES['ROT_X'] | NEG))
    check('example 2: Angle=ROT_X|NEG -> 330', slot_vals(mu)[1], 330)

    # --- FOLLOW
    mu.mem_write(C.HV_TAB, b'\0' * (C.HV_N * C.HV_ENTRY))
    w.strike = 1.15 if w.synthetic else 1.0
    setv(mu, a, w, {0x0F000110: 1.0, 0x0F000111: 0.0, VAR(0): 10.0, VAR(5): 3.0})
    hitbox(mu, a, E, dict(Damage=VAR(0) | FOLLOW, Angle=NAMES['STICK_ANGLE'] | FOLLOW, Size=VAR(5) | FOLLOW,
                          KBG=VAR(2)))
    s0 = slot_vals(mu)
    check('FOLLOW: built (Damage x the game\'s own 1.15 here)', s0, (round(10.0 * w.strike, 4), 0, 71, 0, 30, 3.0))
    check('FOLLOW: an entry for the slot', (r32(mu, C.HV_TAB), r32(mu, C.HV_TAB + 8), r32(mu, C.HV_TAB + 0x10)),
          (ACC, slot_of(mu), 0b100011))
    setv(mu, a, w, {0x0F000110: 0.0, 0x0F000111: 1.0, VAR(0): 20.0, VAR(5): 5.0, VAR(2): 10.0})
    frame(mu, a)
    check('FOLLOW: next frame: Damage 20 (x the ratio), Angle 90 (stick up), Size 5; KBG (no FOLLOW) kept',
          slot_vals(mu), (round(20.0 * w.strike, 4), 90, 71, 0, 30, 5.0))
    check('FOLLOW: the extras still found (check words updated)', ext_find(mu, a, slot_of(mu)) != 0, True)
    setv(mu, a, w, {0x0F000110: -1.0, 0x0F000111: 0.0})
    frame(mu, a, ACC2)
    check('FOLLOW: another object\'s frame: untouched', slot_vals(mu)[1], 90)
    frame(mu, a)
    check('FOLLOW: stick back: 180', slot_vals(mu)[1], 180)
    s = slot_of(mu)
    mu.mem_write(s + C.TAG_OFF, b'\0\0')                    # a plain hitbox in the slot (slot_set clears the tag)
    w32(mu, s + 0x20, 77)
    setv(mu, a, w, {0x0F000110: 0.0, 0x0F000111: -1.0})
    frame(mu, a)
    check('FOLLOW: a later plain hitbox in the slot: not touched, entry freed', (slot_vals(mu)[1], r32(mu, C.HV_TAB)),
          (77, 0))
    hitbox(mu, a, E, dict(Angle=NAMES['STICK_ANGLE'] | FOLLOW))
    check('FOLLOW again: 270', slot_vals(mu)[1], 270)
    hitbox(mu, a, E, dict(Angle=30))
    setv(mu, a, w, {0x0F000110: 1.0, 0x0F000111: 0.0})
    frame(mu, a)
    check('a later Extra hitbox (numbers) in the slot: its next frame keeps its 30 and the FOLLOW entry goes (the tag '
          'changed)', (slot_vals(mu)[1], r32(mu, C.HV_TAB)), (30, 0))
    hitbox(mu, a, E, dict(Angle=NAMES['STICK_ANGLE'] | FOLLOW))
    hitbox(mu, a, E, dict(Angle=VAR(1)))
    check('a later Extra hitbox with variables, no FOLLOW: the FOLLOW entry goes at once', r32(mu, C.HV_TAB), 0)
    hitbox(mu, a, E, dict(Angle=NAMES['STICK_ANGLE'] | FOLLOW))
    setv(mu, a, w, {0x0F000110: 0.0, 0x0F000111: 1.0})
    run(mu, C.WM_RESET, a.addr('hk_wmreset'), {UC_PPC_REG_31: ACC})
    check('the object reset (WM_RESET): its FOLLOW entries go', r32(mu, C.HV_TAB), 0)
    frame(mu, a)
    check('... and its slot isn\'t touched', slot_vals(mu)[1], 0)
    mu.mem_write(C.HV_TAB, b'\0' * (C.HV_N * C.HV_ENTRY))
    for i in range(C.HV_N + 1):                 # 17 FOLLOW hitboxes (2 objects, IDs 0-9): the oldest goes
        acc, ident = (ACC, i) if i < 9 else (ACC2, i - 9)
        f = dict(ID=ident, Angle=NAMES['STICK_ANGLE'] | FOLLOW)
        hitbox(mu, a, E, f, acc=acc)
    used = sorted((r32(mu, C.HV_TAB + C.HV_ENTRY * k), r32(mu, C.HV_TAB + C.HV_ENTRY * k + 8)) for k in range(C.HV_N))
    check('17 FOLLOW hitboxes: 16 entries, the first one gone', ((ACC, SLOTS) in used, (ACC2, SLOTS2 + 0x84 * 7) in used,
                                                                   len(set(used))), (False, True, 16))


def word_diff(patched, base, a, words, hooks):
    import rpx_patch as R
    out = {}
    for path in (patched, base):
        d, _s, _e, secs = R.load(path)
        m = {}
        for s in secs:
            if s[1] == 1 and s[3] and s[5] and s[3] < 0x10000000 and s[2] & 4:
                data = bytes(R.section_data(d, s))
                for i in range(0, len(data) - 3, 4):
                    m[s[3] + i] = struct.unpack_from('>I', data, i)[0]
        out[path] = m
    p, b = out[patched], out[base]
    diff = {k for k in set(p) | set(b) if p.get(k, 0) != b.get(k, 0)}
    want = {C.HV_CODE + 4 * i for i, x in enumerate(a.part6[1]) if x}
    want |= {k for k in (C.FRAME_HOOK, C.WM_RESET, a.addr('gv_zero'), a.addr('cmd_handlers'),
                         a.addr('cmd_handlers') + 4)}
    check('word diff BASE -> PATCHED: only exe_v43\'s words (%d)' % len(want), sorted(hex(k) for k in diff ^ want), [])
    check('BASE: the hooks held v42\'s branches / handlers',
          (b.get(C.FRAME_HOOK), b.get(C.WM_RESET), b.get(a.addr('cmd_handlers')), b.get(a.addr('cmd_handlers') + 4),
           b.get(a.addr('gv_zero'))),
          (C.b(C.FRAME_HOOK, a.addr('hk_frame')), C.b(C.WM_RESET, a.addr('hk_wmreset')), a.addr('h_extra'),
           a.addr('h_extra_ext'), C.b(a.addr('gv_zero'), a.addr('ue_zero'))))
    check('PATCHED: every cave word in place', all(p.get(C.HV_CODE + 4 * i, 0) == x for i, x in enumerate(a.part6[1]))
          and all(p.get(k) == v for k, v in hooks.items() if k < 0x10000000), True)


def main():
    a, words, hooks = C.build()
    if sys.argv[1:2] == ['--synthetic']:
        mu = synthetic_machine(a, words, hooks)
        w = World(mu, a, True)
        setup(mu, w, True)
        tests(mu, a, w)
    else:
        patched, base = sys.argv[1:3]
        word_diff(patched, base, a, words, hooks)
        bm = rpx_machine(base)
        bw = World(bm, a, False)
        setup(bm, bw, False)

        def ref(cmd, fields):
            """BASE (v42): the command's own handler (h_extra) with the values written as numbers -> the slot"""
            bm.mem_write(SLOTS, b'\0' * 0x600)
            hitbox(bm, a, cmd, fields, label='h_extra' if cmd == 'Extra_Special_Hitbox' else 'h_extra_ext')
            return bytes(bm.mem_read(slot_of(bm), 0x68))
        mu = rpx_machine(patched)
        w = World(mu, a, False)
        setup(mu, w, False)
        tests(mu, a, w, ref)
    print('%d failures' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
