#!/usr/bin/env python3
"""Behaviour tests of step 2q (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2q") on a patched
executable, in unicorn (smashrun_step2h_test.py's machine; the game's own functions run natively where named):

  python3 tools/smashrun_step2q_test.py PATCHED.rpx [LOG_2P.txt [PKG_DATA_ROOT [GL_ENEMY_PARAM]]]

LOG_2P.txt (optional): the user's step 2p log build log (upload 947be699): the Big Goomba stomp and the killed Koopa.
PKG_DATA_ROOT (optional): the package's data/ (sound/se/ holds the 19 banks): their file names checked byte for byte
against the names the game builds. GL_ENEMY_PARAM (optional): param/enemy/gl/enemy_param.bin (the White Bear's
gl +0x124, the default ignore_damage threshold).

- the stomp from Jump (the Big Goomba's "no height"): Jump's pre (common MSC func_471) takes kinetic 0x32 when the
  fighter's KineticModule kind (+0x11C, 0x02C510BC; written only by change_kinetic 0x02C4FA00, natively here) is
  still Jump's 1, and the transactor keeps the energies only for 0x32 (0x02E7EE50): no step-jump speed. u_pend: once
  StepJump's main has run (count int 0x10000006 >= 1) and the fighter is in Jump with a kinetic other than 1, it
  writes the mode int 0x11000000 = 1 and float 0x1000006 = the multiplier and calls change_kinetic(1) (the game's
  step jump: 0x02E79938 natively gives 0.9 x step_jump_speed_y); with kinetic 1 (the stomp from JumpAerial) or
  before StepJump ran (count 0) it does nothing; the entry then ends;
- the killed Koopa (state 20): ShellMode once (loop 0, the 3DS's 0x73F80), so it ends: on the ground the shell item is
  thrown and the Koopa is removed (23); the log's kd lines: 240 updates in 20 with frames stepping by 10 (the loop);
- the White Bear's slot 68 (0x7F388): the reaction flag = 1, then no reaction for a damage <= 40 (P0 word 20), or
  for its weak attribute 5 <= the default ignore_damage() (gl +0x124, natively), unless invalid_ignore_damage();
  wb_dmg keeps WB_W through notify_on_damage (slot 68 reads it) and clears it after; the game's notify_on_damage calls
  vt+0x22C with r4 = the flag and f1 = the damage (0x026A35FC-0x026A3614);
- the enemy sound banks: the game's own kind request 0x02DAE314 and battle-start loader 0x02DAE564, natively over the
  field cave's 22 requested kinds, reach the bank creation 0x033EDD24 for every kind (the 19 ported and the 3
  twins, in kind order); the bank registration 0x03673A94 natively: null data -> 0x80000005 and no parse (so no `bk`
  line), data -> the parser path 0x036771D8; the names the game builds (0x10158D64 % the capitalised table
  0x1041A534) are the package's files byte for byte; the resource system's name hash 0x032EAA40 (natively) differs
  for "Kuribo" / "kuribo" (the lookup is case-sensitive).
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
import smashrun_field_cave as F  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

check = T.check
OBJ, INPUT, POSTURE, EN, HEAP, STACK = T.OBJ, T.INPUT, T.POSTURE, T.EN, T.HEAP, T.STACK
FWM, FACC, FPOST, FSTAT = H.FWM, H.FACC, H.FPOST, H.FSTAT
FKM, FKMVT = HEAP + 0x34A00, HEAP + 0x34B00          # the fighter's KineticModule (acc+0x34), its vtable
KM_KIND_STUB, KM_CHANGE_STUB, INVALID_STUB = 0x02000040, 0x02000044, 0x02000048
KM_CHANGE_GAME, KM_KIND_GAME = 0x02C4FA00, 0x02C510BC   # FighterKineticModule vt+0xEC / vt+0xF4 (vtable 0x1012C5C0)
FKM_VTABLE = 0x1012C5C0
TRANSACTOR_KEEP_32 = 0x02E7EE50      # xori r6, r30, 0x32: the transactor's keep-energies flag (kind == 0x32)
NOTIFY_SLOT68 = {0x026A35FC: 0x819F00E0, 0x026A3600: 0x800C022C, 0x026A360C: 0x38810008, 0x026A3610: 0xFC20F890,
                 0x026A3614: 0x4E800421}   # notify_on_damage: vt+0x22C(this, &flag (r1+8), f1 = the damage)
POOL_REQUEST, POOL_LOAD, BANK_CREATE, BANK_REGISTER = 0x02DAE314, 0x02DAE564, 0x033EDD24, 0x03673A94
BANK_PARSE_PATH, NAME_HASH = 0x036771D8, 0x032EAA40
SND_FMT, CAP_NAMES = 0x10158D64, 0x1041A534


class M(H.M):
    """step 2h's machine plus the fighter's KineticModule (its kind, change_kinetic) and invalid_ignore_damage"""

    def __init__(self, img):
        H.M.__init__(self, img)
        self.kin, self.invalid = 1, 0

    def hook(self, u, addr, size, x):
        if addr == KM_KIND_STUB:
            return self.ret(self.kin)
        if addr == KM_CHANGE_STUB:
            self.calls.append(('change_kinetic', u.reg_read(T.R[3]), u.reg_read(T.R[4])))
            self.kin = u.reg_read(T.R[4])
            return self.ret()
        if addr == W.INVALID_IGNORE:
            self.calls.append(('invalid_ignore',))
            return self.ret(self.invalid)
        if addr == W.BI_NOTIFY_DMG:
            self.calls.append(('notify', self.r32(OBJ + W.WB_W)))
            return self.ret()
        return H.M.hook(self, u, addr, size, x)

    def fighter(self, **kw):
        H.M.fighter(self, **kw)
        self.w32(FACC + W.KM_ACC, FKM)
        self.w32(FKM, FKMVT)
        self.w32(FKMVT + W.KM_KIND, KM_KIND_STUB)
        self.w32(FKMVT + W.KM_CHANGE, KM_CHANGE_STUB)


def log_lines(path):
    return open(path, errors='replace').read().splitlines()


def f32(h):
    return struct.unpack('>f', bytes.fromhex(h.zfill(8)))[0]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    H.M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    byname = {w['name']: w for w in W.WALKERS}
    cfg = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    want = {}
    for a in (A.h, A.e, A.g):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'regions E / G / H: the assembled code is in the executable %s' % bad[:4])

    def vslot(name, k):
        vt = img.u32(cfg[name] + W.CF['VT'])
        return img.u32(vt + 0xC + 8 * k)

    def rows(name):
        r = {}
        for sid, s in byname[name]['states'].items():
            if s == 'remove':
                s = (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)
            r[sid] = tuple(x if isinstance(x, int) else fn[x] for x in s)
        return r

    # ---------------------------------------------------------------- the stomp from Jump: the kinetic
    def stomp_then(name, state, after, var=0, at_stomp=0xB):
        """a stomp (fighter in `at_stomp`), then cave-enemy updates with the fighter as `after` says:
        [(status, count int 0x10000006, kinetic kind)]"""
        w = byname[name]
        m = M(img)
        m.walker(cfg[name], state=state, kind=w['kind'], var=var)
        m.wf(POSTURE + 0x14, 0.0)
        m.call(fn['w_init'], {3: OBJ})
        tb = W.tread_box(w)
        top = tb[1] + tb[2] if name != 'tikibuzz' else 11.72 + 1.5    # Tiki Buzz: the box on its node
        m.fighter(y=top + 10.0, status=at_stomp)
        out = []
        for fy in (5.0, -1.0):
            m.wf(FPOST + 0x14, top + fy)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            out.append(list(m.calls))
        for st, cnt, kin in after:
            m.w32(FSTAT + W.STATUS_KIND, st)
            m.work[(FWM, W.I_STEP_COUNT)] = cnt
            m.kin = kin
            m.wf(FPOST + 0x14, top + 30.0)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            out.append([c for c in m.calls if c[0] in ('set_float', 'set_int', 'change_kinetic')])
        pend = [m.r32(D['pend'] + 12 * i + 8) for i in range(4)]
        return m, out, pend
    # the Big Goomba from Jump: before the fighter's update (count 0) nothing; after it (count 1, kinetic 0x32): the
    # step jump; the next update nothing (the entry ended)
    m, got, pend = stomp_then('dekakuribo', 3, [(0xB, 0, 1), (0xB, 1, 0x32), (0xB, 1, 1)])
    check(('msc_status', FACC, (3, W.STEP_JUMP, 0)) in got[1] and got[2] == [] and
          got[3] == [('set_int', FWM, 1, W.I_JUMP_MODE), ('set_float', FWM, W.F_TREAD_MUL, 0.9),
                     ('change_kinetic', FKM, 1)] and got[4] == [] and pend == [0, 0, 0, 0] and
          m.work[(FWM, W.I_JUMP_MODE)] == 1 and m.work[(FWM, W.F_TREAD_MUL)] == 0.9,
          'Big Goomba stomped from Jump: nothing while StepJump has not run (count 0); once it has and the fighter '
          'is in Jump with kinetic 0x32: mode int 0x11000000 = 1, float 0x1000006 = 0.9, change_kinetic(1); the '
          'entry ended %s' % ((got[2:], pend),))
    m, got, pend = stomp_then('kuribo', 3, [(0xB, 1, 1), (0xB, 1, 1)], at_stomp=0xC)
    check(got[2] == [] and got[3] == [] and pend == [0, 0, 0, 0],
          'Goomba stomped from JumpAerial (the chain took kinetic 1: the game\'s own step jump): no change, the entry '
          'ended %s' % ((got[2:], pend),))
    m, got, pend = stomp_then('patapata', 12, [(0xE, 1, 0x32), (0x1D, 1, 0x32)], var=2)
    check(got[2] == [] and got[3] == [],
          'the fighter in another status after the stomp (0xE, 0x1D): no kinetic change %s' % got[2:])
    m, got, pend = stomp_then('tikibuzz', 3, [(W.STEP_JUMP, 1, 0x33), (0xB, 1, 0x32)])
    check(got[2] == [('set_float', FWM, W.F_TREAD_MUL, 0.98)] and
          got[3] == [('set_int', FWM, 1, W.I_JUMP_MODE), ('set_float', FWM, W.F_TREAD_MUL, 0.98),
                     ('change_kinetic', FKM, 1)],
          'Tiki Buzz: StepJump seen (the multiplier re-written), then Jump with 0x32: the step jump %s' % got[2:])

    # the KineticModule natively: change_kinetic (vt+0xEC) runs the transactor, then stores +0x11C; vt+0xF4 reads it
    m = M(img)
    km, tr, trvt = HEAP + 0x3A000, HEAP + 0x3A400, HEAP + 0x3A500
    m.w32(km + 0x124, tr)
    m.w32(tr, trvt)
    m.w32(trvt + 0x4C, KM_CHANGE_STUB)
    m.w32(km + 0x11C, 1)
    seen = []

    def run(fn_, regs):
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(fn_, T.DONE, regs)
        return m.uc.reg_read(T.R[3])
    m.calls = []
    run(KM_CHANGE_GAME, {3: km, 4: 0x32})
    seen.append(m.r32(km + 0x11C))
    k = run(KM_KIND_GAME, {3: km})
    check(img.u32(FKM_VTABLE + W.KM_CHANGE) == KM_CHANGE_GAME and img.u32(FKM_VTABLE + W.KM_KIND) == KM_KIND_GAME
          and [c[2] for c in m.calls if c[0] == 'change_kinetic'] == [0x32] and seen == [0x32] and k == 0x32 and
          img.u32(TRANSACTOR_KEEP_32) == 0x6BC60032,
          'FighterKineticModule (vtable 0x1012C5C0): change_kinetic 0x02C4FA00 runs the transactor (its vt+0x4C) then '
          'stores the kind at +0x11C, which vt+0xF4 0x02C510BC returns (Jump\'s pre reads it: 0x32 when it is 1); '
          'the transactor keeps the energies only for 0x32 (0x02E7EE50)')

    # the game's StepJump speed with our writes (count 1 after StepJump's main: no pow factor)
    def speed(mult, count):
        mm = M(img)
        lo_, hi_ = W.STEP_JUMP_SPEED, W.STEP_JUMP_SPEED + 0x340
        for a in range(lo_, hi_, 4):
            if img.u32(a) >> 26 == 4:
                mm.uc.mem_write(a, struct.pack('>I', 0x60000000))
        mm.fighter()
        mm.params = {0x300015F: 2.4, 0x3000160: 1.5, 0x300000D: 0.0, 0x300000E: 0.0, 0x300000F: 1.0, 0x20000B5: 0.8}
        mm.work[(FWM, W.F_TREAD_MUL)] = mult
        mm.work[(FWM, W.I_STEP_COUNT)] = count
        mm.wf(HEAP + 0x3F000, 0.0)
        mm.wf(HEAP + 0x3F004, 0.0)
        mm.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        mm.run(W.STEP_JUMP_SPEED, T.DONE, {3: HEAP + 0x3E000, 4: HEAP + 0x3F000, 5: FACC})
        return round(mm.rf(HEAP + 0x3F004), 4)
    sp = speed(0.9, 1)
    check(sp == round(2.4 * 0.9, 4), 'the step jump our change_kinetic(1) makes: 0x02E79938 with float 0x1000006 = 0.9 '
          'and count 1 gives 0.9 x step_jump_speed_y = %s' % sp)

    # ---------------------------------------------------------------- the killed Koopa (state 20)
    m = M(img)
    m.walker(cfg['patapata'], state=20, kind=3, var=3)
    m.target, m.target_x = 0, 300.0
    m.call(fn['w_init'], {3: OBJ})
    wo = T.World(m, byname['patapata'], rows('patapata'), 20, cfg['patapata'])
    first = list(m.calls)
    m.vy = -0.5
    wo.run(12)
    thr = [x for e in wo.log for x in e[4] if x[0] == 'throw']
    mot = [c for c in first if c[0] == 'motion']
    check(mot == [('motion', OBJ, 18, 0.0, 10.0, 0, 0.0)] and wo.states() == [20, 23] and len(thr) == 1 and
          thr[0][1:3] == (0x46, 0),
          'killed Koopa: 20 plays ShellMode once at 10 (the 3DS\'s loop false, 0x73F80), so it ends: on the ground the '
          'shell item is thrown (the Green Shell 0x46 for 0x94) and it is removed (23) %s' % ((mot, wo.states(), thr),))

    # ---------------------------------------------------------------- the White Bear's armor (slot 68)
    gl124 = 0.0
    if len(sys.argv) > 4:
        gl124 = gl_float(sys.argv[4], 0x40, 0x124)
    p17 = struct.unpack('>f', struct.pack('>I', img.u32(cfg['whitebear'] + W.P(17))))[0]

    def slot68(dmg, weak, invalid=0):
        m = M(img)
        m.walker(cfg['whitebear'], state=3, kind=0x40)
        m.w32(H.GLTAB + 0x124, struct.unpack('>I', struct.pack('>f', gl124))[0])
        m.w32(OBJ + W.WB_W, weak)
        m.invalid = invalid
        flag = HEAP + 0x3C000
        m.uc.mem_write(flag, b'\x07')
        m.calls = []
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(vslot('whitebear', 68), T.DONE, {3: OBJ, 4: flag}, {1: dmg})
        return m.uc.mem_read(flag, 1)[0], [c[0] for c in m.calls]
    res = {(dmg, weak, inv): slot68(dmg, weak, inv)[0] for dmg, weak, inv in
           ((10.0, 0, 0), (40.0, 0, 0), (40.5, 0, 0), (25.0, 0, 1), (60.0, 0, 0),
            (gl124, 1, 0), (gl124 + 0.5, 1, 0), (10.0, 1, 0))}
    exp = {(10.0, 0, 0): 0, (40.0, 0, 0): 0, (40.5, 0, 0): 1, (25.0, 0, 1): 1, (60.0, 0, 0): 1,
           (gl124, 1, 0): 0, (gl124 + 0.5, 1, 0): 1, (10.0, 1, 0): int(10.0 > gl124)}
    check(vslot('whitebear', 68) == fn['wb_68'] and p17 == 40.0 and res == exp and
          all(img.u32(a) == w for a, w in NOTIFY_SLOT68.items()),
          'White Bear slot 68 (0x7F388): reaction off for a damage <= 40 (P0 word 20), on above it or when '
          'invalid_ignore_damage(); a weak (attribute 5) hit against the default ignore_damage() (gl +0x124 = %s); the '
          'game\'s notify_on_damage calls vt+0x22C(&flag, f1 damage) %s' % (gl124, res))

    def wbdmg(weak):
        m = M(img)
        m.walker(cfg['whitebear'], state=3, kind=0x40)
        m.w32(OBJ + W.WB_W, weak)
        m.damage = 12.0
        m.wf(OBJ + W.WB_D, 2.0)
        m.calls = []
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(byname_fdmg(cfg, img), T.DONE, {3: OBJ})
        return [c for c in m.calls if c[0] in ('notify', 'set_damage')], m.r32(OBJ + W.WB_W)
    calls1, after1 = wbdmg(1)
    calls0, after0 = wbdmg(0)
    check(calls1 == [('set_damage', OBJ, 22.0), ('notify', 1)] and after1 == 0 and calls0 == [('notify', 0)] and
          after0 == 0,
          'wb_dmg: the weak hit doubled (12 - 2 = 10 added again: 22), WB_W still set when notify_on_damage runs '
          '(slot 68 reads it), cleared after %s' % ((calls1, after1, calls0, after0),))

    # ---------------------------------------------------------------- the sound banks
    sound_tests(img, check, sys.argv[3] if len(sys.argv) > 3 else None)

    # ---------------------------------------------------------------- the log (optional)
    if len(sys.argv) > 2:
        lines = log_lines(sys.argv[2])
        hs = [i for i, ln in enumerate(lines) if 'S4N hs k=23' in ln]
        ys, fst = [], None
        if hs:
            mm = re.search(r'fst=(\w+) fy=(\w+)', lines[hs[0]])
            fst, ys = int(mm.group(1), 16), [f32(mm.group(2))]
            for ln in lines[hs[0] + 1:hs[0] + 200]:
                p = re.search(r'S4N pd .*fy=(\w+)', ln)
                if p and f32(p.group(1)) != ys[-1]:
                    ys.append(f32(p.group(1)))
                if len(ys) > 5:
                    break
        dys = [round(b - a, 2) for a, b in zip(ys, ys[1:])]
        check(fst == 0xB and dys[1:4] == [-0.11, -0.22, -0.32],
              'the step 2p log: the Big Goomba stomp came with the fighter in Jump (fst=B) and it fell from rest (dy '
              '%s: speed 0, the 0x33 reset kept by Jump\'s 0x32)' % dys)
        kd = [ln for ln in lines if 'S4N kd' in ln]
        last_dm = max(i for i, ln in enumerate(lines) if 'S4N dm' in ln)
        after = [dict(x.split('=') for x in ln.split('S4N kd ')[1].split()) for ln in lines[last_dm:] if 'S4N kd' in ln]
        frames = [round(f32(a['fr'])) for a in after[:8]]
        steps = {(b - a) % 16 for a, b in zip(frames, frames[1:])}
        check(len(kd) == 1200 and after and all(a['s'] == '14' and a['m'] == '12' for a in after) and steps == {10},
              'the step 2p log: after the Koopa\'s last hit it stayed in 20 (0x14) with ShellMode (motion 0x12) for '
              'all '
              '%d kd updates, the frame stepping by 10 mod 16 (%s): the looping rate-10 spin' % (len(after), frames))

    T.overrun_check()
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


def byname_fdmg(cfg, img):
    """the bear's slot 10 handler (CFG FDMG: wb_dmg)"""
    return img.u32(cfg['whitebear'] + W.CF['FDMG'])


def gl_float(path, kind, off):
    """param/enemy/gl/enemy_param.bin group 3, entry kind + 1, the value at off (tools/smashrun_step2n_test.py's
    reading of the file)"""
    import fighter_param_vl as V
    _h, toks = V.tokenize(open(path, 'rb').read())
    groups = []
    for t in toks:
        if isinstance(t, tuple):
            groups.append([])
        else:
            groups[-1].append(t)
    g = groups[2]
    n = len(g) // 99
    return float(g[(kind + 1) * n + off // 4].value)


def sound_tests(img, check, pkg_root):
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn.ppc_const import UC_PPC_REG_MSR
    R = T.R
    u = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
    u.mem_map(0x02000000, 0x03000000)
    u.mem_map(0x10000000, 0x00800000)
    for base, data in img.mem:
        if 0x02000000 <= base < 0x05000000 or 0x10000000 <= base < 0x10800000:
            u.mem_write(base, data[:max(0, min(len(data), 0x05000000 - base))] if base < 0x05000000 else data)
    WORK = 0x30000000
    u.mem_map(WORK, 0x01000000)
    done = 0x30FF0000
    u.mem_write(done, struct.pack('>I', 0x48000000))
    bump = [WORK + 0x100000]

    def new_n(n):
        a = bump[0]
        bump[0] += (n + 15) & ~15
        u.mem_write(a, b'\0' * n)
        return a
    st = {}

    def hook(uc, addr, size, _):
        if addr in st:
            r = st[addr](uc)
            if r is not None:
                uc.reg_write(R[3], r & 0xFFFFFFFF)
            uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
    u.hook_add(UC_HOOK_CODE, hook)

    def call(f, args):
        for i, a in enumerate(args):
            u.reg_write(R[3 + i], a & 0xFFFFFFFF)
        u.reg_write(R[1], WORK + 0xF00000)
        u.reg_write(UC_PPC_REG_LR, done)
        u.reg_write(UC_PPC_REG_MSR, u.reg_read(UC_PPC_REG_MSR) | 0x2000)
        u.emu_start(f, done, count=2000000)
        return u.reg_read(R[3])
    r3 = lambda uc: uc.reg_read(R[3])  # noqa: E731
    requests, banks, effects = [], [], []
    st.update({0x03376098: lambda uc: new_n(uc.reg_read(R[3])),               # operator new
               0x030BF400: lambda uc: requests.append(uc.reg_read(R[4])),     # the file requests (model ... sound)
               0x032FF4FC: r3, 0x032FF580: r3, 0x032FF61C: lambda uc: None, 0x033EBAD0: r3, 0x033EBFEC: r3,
               0x033EBE74: lambda uc: None})
    G, PM, POOL = new_n(0x100), new_n(0x40), new_n(0x80)
    u.mem_write(0x102F9028, struct.pack('>I', G))
    u.mem_write(G + 0x54, struct.pack('>I', PM))
    for off in (0, 0xC, 0x18):                       # the pool's three maps (kind -> model / effect / sound holder)
        h = new_n(0x18)
        u.mem_write(h, struct.pack('>III', h, h, h) + b'\0' * 8 + b'\x01\x01\0\0')
        u.mem_write(POOL + off, struct.pack('>III', 0, h, 0))
    for k in F.REQUESTS:
        call(POOL_REQUEST, (POOL, k))

    def h61c(uc):
        out, kind, typ = uc.reg_read(R[4]), uc.reg_read(R[5]), uc.reg_read(R[6])
        uc.mem_write(out, struct.pack('>I', 0xAB000000 | kind << 8 | typ))
        return out

    def cp(uc):
        uc.mem_write(uc.reg_read(R[3]), bytes(uc.mem_read(uc.reg_read(R[4]), 4)))
        return uc.reg_read(R[3])

    def mkbank(uc):
        hv = struct.unpack('>I', bytes(uc.mem_read(uc.reg_read(R[5]), 4)))[0]
        banks.append((hv >> 8) & 0xFF if hv & 0xFF == 4 else -1)
    st.update({0x030BF61C: h61c, 0x032D69B8: cp, 0x032D4200: lambda uc: None,
               0x032D3E3C: lambda uc: (uc.mem_write(uc.reg_read(R[3]), b'\0' * 4), uc.reg_read(R[3]))[1],
               0x03305068: lambda uc: None, 0x02DC6DA8: lambda uc: 0,
               0x02DAE48C: lambda uc: (effects.append(uc.reg_read(R[4])), 1)[1], BANK_CREATE: mkbank,
               0x033EBFBC: lambda uc: None})
    call(POOL_LOAD, (POOL,))
    ported = sorted({k for k in F.REQUESTS if k < 0x50})
    check(requests == list(F.REQUESTS) and banks == sorted(F.REQUESTS) and len(ported) == 19,
          'sounds: the game\'s kind request 0x02DAE314 (natively, the field cave\'s %d kinds) fills the pool\'s sound '
          'map, and its battle-start loader 0x02DAE564 (natively) creates a bank (0x033EDD24) from each kind\'s type-4 '
          'file, ours and the twins alike: %s' % (len(requests), [hex(b) for b in banks]))

    # the bank registration: null data -> 0x80000005 (0x03673B50), no parse; data -> the parser path
    parsed = []
    st.clear()
    st[BANK_PARSE_PATH] = lambda uc: (parsed.append(uc.reg_read(R[3])), 0)[1]
    u.mem_write(0x10446604, b'\x01\x00')
    rc0 = call(BANK_REGISTER, (0, 0x1000, 0))
    rc1 = call(BANK_REGISTER, (WORK + 0x200000, 0x1000, 0))
    check(rc0 == 0x80000005 and rc1 == 0 and parsed == [WORK + 0x200000],
          'sounds: 0x03673A94 (natively) returns 0x80000005 for a bank with no data and never reaches the parser %s '
          '(no '
          '`bk` line: the step 2p log has none for our 19 banks), a bank with data goes on to 0x036771D8 -> the parser'
          % ((hex(rc0), hex(rc1), [hex(x) for x in parsed]),))

    # the names the game builds, and the resource lookup's case-sensitive hash
    def cstr(a):
        out = b''
        while True:
            c = img.u8(a) if hasattr(img, 'u8') else (img.u32(a & ~3) >> (24 - 8 * (a & 3))) & 0xFF
            if not c:
                return out.decode()
            out += bytes([c])
            a += 1
    fmt = cstr(SND_FMT)
    names = {k: fmt % cstr(img.u32(CAP_NAMES + 4 * k)) for k in sorted(set(F.REQUESTS))}
    hs = {}
    for s in ('snd_se_enemy_Kuribo.nus3bank', 'snd_se_enemy_kuribo.nus3bank'):
        a = WORK + 0x300000
        u.mem_write(a, s.encode())
        hs[s] = call(NAME_HASH, (a, len(s)))
    check(fmt == 'sound/se/snd_se_enemy_%s.nus3bank' and names[1] == 'sound/se/snd_se_enemy_Kuribo.nus3bank' and
          len(set(hs.values())) == 2,
          'sounds: the path 0x030BC868 builds = %r %% the capitalised name (Kuribo: %s); the resource system\'s name '
          'hash 0x032EAA40 (natively) of "Kuribo" / "kuribo": %s (case-sensitive: a lower-case file is another name)'
          % (fmt, names[1], {k: hex(v) for k, v in hs.items()}))
    if pkg_root:
        se = os.path.join(pkg_root, 'sound', 'se')
        have = set(os.listdir(se))
        want = {os.path.basename(names[k]) for k in names if k < 0x50}
        check(want <= have and len(want) == 19,
              'sounds: the package\'s 19 banks carry the exact names the game opens %s' % sorted(want - have))


if __name__ == '__main__':
    main()
