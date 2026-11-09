#!/usr/bin/env python3
"""Behaviour tests of step 2r (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2r") on a patched
executable, in unicorn (smashrun_step2q_test.py's machine; the game's own functions run natively where named):

  python3 tools/smashrun_step2r_test.py PATCHED.rpx [CODE_BIN_3DS [LOG_2P.txt]]

CODE_BIN_3DS (optional): the decompressed 3DS code.bin (tools/s3ds_unpack.py code): the readings the area test rests
on, checked word by word. LOG_2P.txt (optional): the step 2p log (upload 947be699): its Big Goomba stomp and the fall
before it replayed through the new test.

- the readings: the 3DS rect area's bounds are its centre +- size x 0.5 (0x41FE7C, the 0.5 at 0x41FF00), offset and
  size scaled by the node matrix's scale (0x3D9278-0x3D92C4), two areas touch when their boxes overlap (0x9E57BC);
  the Wii U auto-tread 0x02E67534 (mode 1: not in StepJump, the target, falling: KineticModule vt+0xA4(1) y < 0),
  the situation at StatusModule +0x84 (vt+0xDC 0x02E885E0), get_sum_speed 0x02C508EC; the four kinds' boxes from
  their vl P5[0] (half size x the gl scale, the centre on the node);
- the stomp test (w_upd, every stompable kind: Goomba, Big Goomba, Paratroopa (winged and walking), Tiki Buzz) over a
  grid of x offsets, starting heights and fall speeds up to 60 a frame, against the model: the feet's fall over the
  frame [now, last] meets [bottom, top] relative to the box, the x ranges overlap (the fighter's x extent from its
  area 0, clamped to FT_EXT_MAX), the fighter in the air, not in StepJump, falling (speed y < 0), no bounce pending;
- the bounce after the stomp: for each status the stomp can come in (Jump 0xB, JumpAerial 0xC, Fall 0xD, FallAerial
  0xE) the kinetic Jump's pre takes (func_471: 0x32 when the kind is 1, else 1), then u_pend once StepJump has run:
  mode int 0x11000000 = 1, float 0x1000006 = the kind's multiplier, change_kinetic(1); the game's kinetic-1 dispatch
  0x02E7A4DC run natively with that mode gives the step jump 0x02E79938 (Big Goomba 0.9 x step_jump_speed_y); a speed
  lost while still in Jump in the watch window (PEND_VER updates) gets the step jump again, once; a status change
  ends the watch.
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
import smashrun_step2q_test as Q  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_LR  # noqa: E402

check = T.check
OBJ, INPUT, POSTURE, HEAP = T.OBJ, T.INPUT, T.POSTURE, T.HEAP
FWM, FACC, FPOST, FSTAT, FKM = H.FWM, H.FACC, H.FPOST, H.FSTAT, Q.FKM
AM, ALIST, AENTS, AINST = (HEAP + 0x3B000 + 0x100 * i for i in range(4))
KIND_DISPATCH = 0x02E7A4DC          # FighterKineticTransactor: the per-kind energy set-up (r4 kind, r5 &speed, r6 acc)
KD_STEP_OUT, KD_JUMP_OUT = 0x02E7A41C, 0x02E7A198     # kind 1: mode 1 -> 0x02E79938 then 0x02E7A41C; else 0x02E7A198
TREAD_STATE = {('kuribo', 0): 8, ('dekakuribo', 0): 10, ('patapata', 0): 9, ('patapata', 2): 19,
               ('tikibuzz', 0): 10}
START_STATE = {('kuribo', 0): 3, ('dekakuribo', 0): 3, ('patapata', 0): 2, ('patapata', 2): 12, ('tikibuzz', 0): 3}
TIKI_NODE_Y = 11.72                 # smashrun_walker_test's node_gpos default (Tiki Buzz's HipN bind height)


class M(Q.M):
    """step 2q's machine plus the fighter's AreaModule (acc+0x60: its area 0's min x / max x) and the kind dispatch's
    outputs"""

    def __init__(self, img):
        Q.M.__init__(self, img)
        self.out_vec = []

    def hook(self, u, addr, size, x):
        if addr in (KD_STEP_OUT, KD_JUMP_OUT):
            p = u.reg_read(T.R[4])
            self.out_vec.append((addr, round(self.rf(p), 4), round(self.rf(p + 4), 4)))
            return self.ret()
        return Q.M.hook(self, u, addr, size, x)

    def area0(self, minx=None, maxx=None):
        self.w32(FACC + W.FT_AREA, AM if minx is not None else 0)
        self.w32(AM + 0xC, ALIST)
        self.w32(ALIST + 4, 1)
        self.w32(ALIST + 8, AENTS)
        self.w32(AENTS + 4, AINST)
        if minx is not None:
            self.wf(AINST + 0x2C, minx)
            self.wf(AINST + 0x34, maxx)


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
    for a in (A.h, A.stomp, A.area):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'regions C / D / H: the assembled code is in the executable %s' % bad[:4])

    # ---------------------------------------------------------------- the readings
    wu = {0x02E67558: 0x3C801000, 0x02E6756C: 0x38840008, 0x02E67598: 0x2C0300B3, 0x02E675C4: 0x3C802000,
          0x02E675CC: 0x38840005, 0x02E675D0: 0x2C1F0000, 0x02E67614: 0x800800A4, 0x02E67620: 0x38800001,
          0x02E67638: 0xFC0D0000, 0x02E885E0: 0x80630084, 0x02C508EC: 0x9421FFE8}
    vt_ok = img.u32(Q.FKM_VTABLE + W.KM_SPEED) == 0x02C508EC and img.u32(0x1012D42C + 0xDC) == 0x02E885E0
    check(all(img.u32(a) == w for a, w in wu.items()) and vt_ok,
          'Wii U: the auto-tread 0x02E67534 reads int 0x10000008, skips status 0xB3, tests flag 0x20000005 by mode '
          '(r31), and in mode 1 KineticModule vt+0xA4(1) (get_sum_speed 0x02C508EC) y against 0; the situation is '
          'StatusModule +0x84 (FighterStatusModule vt+0xDC 0x02E885E0) %s'
          % [hex(a) for a, w in wu.items() if img.u32(a) != w])
    if len(sys.argv) > 2:
        cb = open(sys.argv[2], 'rb').read()
        u3 = lambda a: struct.unpack('<I', cb[a - 0x100000:a - 0x100000 + 4])[0]  # noqa: E731
        ds = {0x41FE84: 0xED9F0A1D,      # vldr s0, [pc, #0x74]: the 0.5 at 0x41FF00
              0x41FE90: 0xEE600A80,      # vmul s1, s1, s0 (width x 0.5)
              0x41FE94: 0xEE211A00,      # vmul s2, s2, s0 (height x 0.5)
              0x41FF00: 0x3F000000,      # 0.5
              0x3D92A4: 0xE35005FE,      # cmp r0, #0x3f800000 (the node scale 1.0: nothing scaled)
              0x3D92B0: 0xEE288A00,      # vmul s16, s16, s0 (a circle's radius / the size x the scale)
              0x3D92B4: 0xEE600A80,      # vmul s1, s1, s0 (the offset x the scale)
              0x9E57BC: 0xED920A0C,      # vldr s0, [r2, #0x30]: one box's max x ...
              0x9E57C0: 0xEDD00A0A,      # vldr s1, [r0, #0x28]: ... against the other's min x
              0x73DD2C: 0xEB0A9E8A}      # bl 0x9E575C (the contact test between two area instances)
        got3 = {a: u3(a) for a in ds}
        check(got3 == ds, '3DS: rect bounds = centre +- size x 0.5 (0x41FE7C, 0.5 at 0x41FF00), offset / size x the '
              'node scale when it is not 1.0 (0x3D92A4), the area contact a box overlap (0x73DD2C -> 0x9E575C, rect / '
              'rect 0x9E57BC) %s' % {hex(a): hex(v) for a, v in got3.items() if ds[a] != v})
    ok, rows = True, []
    for name, node_y in (('kuribo', 2.53), ('dekakuribo', 0.0), ('patapata', 0.0)):
        e = W.vl_group(name, 5)[0]           # {on, node, w, h, ox, oy}
        s = W.TREAD_SCALE[name]
        model = (e[2] * 0.5 * s, (node_y + e[5]) * s, e[3] * 0.5 * s)
        tb = W.tread_box(byname[name])
        rows.append((name, tuple(e), s, tuple(round(v, 3) for v in tb)))
        ok &= all(abs(a - b) < 1e-3 for a, b in zip(model, tb))
    check(ok, 'the tread boxes are the 3DS areas (vl P5[0] {on, node, w, h, ox, oy}: half width w / 2, centre (node '
          'bind y + oy), half height h / 2, all x the gl scale) %s' % rows)

    # ---------------------------------------------------------------- the stomp test: the grid
    def box(name):
        tb = W.tread_box(byname[name])
        base = TIKI_NODE_Y if name == 'tikibuzz' else 0.0
        return tb[0], base + tb[1] + tb[2], tb[2]

    def run(m, name, var, frames, ext=None, situ=W.SITU_AIR, status=0xB, fvy=-2.0, pend=False):
        """frames: (fighter x, feet y) per frame; the enemy at (0, 0) in its start state -> the frame of the stomp
        (StepJump requested) or None"""
        st = START_STATE[(name, var)]
        m.walker(cfg[name], state=st, kind=byname[name]['kind'], var=var)
        m.damage = 0.0                     # the Big Goomba's HP whole again (H.M keeps HP = max - damage)
        m.wf(H.EN, m.maxhp)
        m.wf(H.EN + 4, m.maxhp)
        m.wf(POSTURE + 0x14, 0.0)
        m.call(fn['w_init'], {3: OBJ})
        m.fighter(y=frames[0][1], x=frames[0][0], status=status, situation=situ)
        m.area0(*((frames[0][0] - ext, frames[0][0] + ext) if ext is not None else (None, None)))
        m.fvy = fvy
        m.uc.mem_write(D['pend'], bytes(48))
        if pend:
            m.w32(D['pend'], FACC)
            m.w32(D['pend'] + 8, 5)
        for i, (fx, fy) in enumerate(frames):
            m.wf(FPOST + 0x10, fx)
            m.wf(FPOST + 0x14, fy)
            if ext is not None:
                m.wf(AINST + 0x2C, fx - ext)
                m.wf(AINST + 0x34, fx + ext)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            if any(c[0] == 'msc_status' for c in m.calls):
                chg = [c[2] for c in m.calls if c[0] == 'chgi']
                return i, chg
        return None

    def expect(p, n, dx, hw, hh, ext):
        return n < p and n <= 0.0 and p >= -2.0 * hh and abs(dx) <= hw + min(max(ext, 0.0), W.FT_EXT_MAX)
    total, bad = 0, []
    kinds = (('kuribo', 0), ('dekakuribo', 0), ('patapata', 0), ('patapata', 2), ('tikibuzz', 0))
    for name, var in kinds:
        m = M(img)
        hw, top, hh = box(name)
        for ext in (None, 3.0, 12.0):
            e = 0.0 if ext is None else ext
            reach = hw + min(e, W.FT_EXT_MAX)
            dxs = sorted({round(reach + k * 0.5, 2) * sg for k in range(-4, 4) for sg in (1, -1)} | {0.0})
            for dx in dxs:
                for start in (6.0, 0.5, -0.5, -2 * hh + 0.25, -2 * hh - 0.5):
                    for spd in (0.3, 1.5, 4.0, 11.0, 24.0, 60.0):
                        p, n = start, start - spd
                        r = run(m, name, var, [(dx, top + p), (dx, top + n)], ext=ext)
                        exp = expect(p, n, dx, hw, hh, e)
                        total += 1
                        got = r is not None and r[0] == 1
                        if got != exp or (got and r[1] != [TREAD_STATE[(name, var)]]):
                            bad.append((name, var, ext, dx, p, n, r))
    check(not bad, 'the stomp grid (5 kinds x 3 fighter boxes x x offsets around the edge x 5 starting heights x 6 '
          'fall speeds up to 60 a frame = %d falls): a stomp exactly when the feet\'s fall over the frame meets the '
          'box (top / bottom) and the x ranges overlap (the fighter\'s area 0 clamped to %g a side), into the kind\'s '
          'tread state %s' % (total, W.FT_EXT_MAX, bad[:6]))
    # the exclusions, each on a fall that is a stomp otherwise (the Big Goomba, dx 2, 3 above the top -> 1 inside)
    m = M(img)
    hw, top, hh = box('dekakuribo')
    fall = [(2.0, top + 3.0), (2.0, top - 1.0)]
    res = {'plain': run(m, 'dekakuribo', 0, fall), 'ground': run(m, 'dekakuribo', 0, fall, situ=0),
           'ledge': run(m, 'dekakuribo', 0, fall, situ=1), 'stepjump': run(m, 'dekakuribo', 0, fall, status=0xB3),
           'not falling': run(m, 'dekakuribo', 0, fall, fvy=0.0), 'rising': run(m, 'dekakuribo', 0, fall, fvy=1.0),
           'pending': run(m, 'dekakuribo', 0, fall, pend=True), 'first frame': run(m, 'dekakuribo', 0, fall[1:]),
           'side entry': run(m, 'dekakuribo', 0, [(hw + 4.0, top - 1.0), (hw - 0.5, top - 1.5)]),
           'side, no fall': run(m, 'dekakuribo', 0, [(hw + 4.0, top - 1.0), (hw - 0.5, top - 1.0)]),
           'rises into it': run(m, 'dekakuribo', 0, [(2.0, top - 3.0), (2.0, top - 1.0)], fvy=1.0)}
    exp = {'plain': (1, [10]), 'side entry': (1, [10])}
    check(all(res[k] == exp.get(k) for k in res),
          'no stomp on the ground (situation 0) or a ledge (1), in StepJump, not falling (speed y >= 0: the game\'s '
          'own condition), with a bounce pending, on the first frame, standing in it, rising into it; one on a fall '
          'into it from the side (the 3DS\'s overlap: the old test needed a crossing of the top) %s' % res)

    # ---------------------------------------------------------------- the bounce after the stomp
    def kind_dispatch(mode, mult, count=1):
        """0x02E7A4DC natively for kinetic 1 with the mode int: (the output function, x, y)"""
        mm = M(img)
        lo_, hi_ = KIND_DISPATCH, KIND_DISPATCH + 0x4900
        for a in range(lo_, hi_, 4):
            if img.u32(a) >> 26 == 4:
                mm.uc.mem_write(a, struct.pack('>I', 0x60000000))
        for a in range(W.STEP_JUMP_SPEED, W.STEP_JUMP_SPEED + 0x340, 4):
            if img.u32(a) >> 26 == 4:
                mm.uc.mem_write(a, struct.pack('>I', 0x60000000))
        mm.fighter()
        mm.params = {0x300015F: 2.4, 0x3000160: 1.5, 0x300000D: 0.0, 0x300000E: 0.0, 0x300000F: 1.0, 0x20000B5: 0.8}
        mm.work[(FWM, W.I_JUMP_MODE)] = mode
        mm.work[(FWM, W.F_TREAD_MUL)] = mult
        mm.work[(FWM, W.I_STEP_COUNT)] = count
        sp = HEAP + 0x3F000
        mm.wf(sp, 0.0)
        mm.wf(sp + 4, 0.0)
        mm.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        mm.run(KIND_DISPATCH, T.DONE, {3: HEAP + 0x3E000, 4: W.KINETIC_JUMP, 5: sp, 6: FACC})
        return mm.out_vec
    kd1 = kind_dispatch(1, 0.9)
    kd0 = kind_dispatch(0, 0.9)
    check(kd1 == [(KD_STEP_OUT, 0.0, round(2.4 * 0.9, 4))] and kd0 and kd0[0][0] == KD_JUMP_OUT and
          all(v[0] != KD_STEP_OUT or v[2] == 0.0 for v in kd0),
          'the game\'s kinetic-1 set-up 0x02E7A4DC natively: mode int 0x11000000 = 1 -> the step jump 0x02E79938 '
          '(Big Goomba 0.9 x step_jump_speed_y 2.4 = 2.16) into 0x02E7A41C; mode 0 -> the plain jump 0x02E7A198 '
          '%s %s' % (kd1, kd0))

    def bounce(name, var, pre_status, pre_kind, seq):
        """a stomp with the fighter in pre_status (kinetic pre_kind), the fighter's update (StepJump -> Jump, Jump's
        pre: func_471), then u_pend each update with seq [(status, speed y)] -> (Jump's kinetic, the calls per
        update, the entry's count word)"""
        m = M(img)
        hw, top, hh = box(name)
        r = run(m, name, var, [(1.0, top + 2.0), (1.0, top - 0.5)], status=pre_status)
        assert r is not None, (name, pre_status)
        jump_kin = 0x32 if pre_kind == 1 else 1            # func_471
        m.kin = jump_kin
        m.work[(FWM, W.I_STEP_COUNT)] = 1                  # StepJump's main (func_1145: count + 1)
        out = []
        for st, vy in seq:
            m.w32(FSTAT + W.STATUS_KIND, st)
            m.fvy = vy
            m.wf(FPOST + 0x14, top + 20.0)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            out.append([c[:1] + c[2:] for c in m.calls if c[0] in ('set_float', 'set_int', 'change_kinetic')])
        return jump_kin, out, m.r32(D['pend'] + 8), m.kin
    mul = {'dekakuribo': 0.9, 'kuribo': 0.8, 'patapata': 1.0, 'tikibuzz': 0.98}
    app = lambda k: [('set_int', 1, W.I_JUMP_MODE), ('set_float', W.F_TREAD_MUL, mul[k]),  # noqa: E731
                     ('change_kinetic', 1)]
    table, ok = [], True
    for pre, kin in ((0xB, 1), (0xC, 2), (0xD, 0x32), (0xE, 0x13)):
        for name, var in (('dekakuribo', 0), ('kuribo', 0), ('patapata', 2), ('tikibuzz', 0)):
            jk, out, cw, kin_after = bounce(name, var, pre, kin, [(0xB, 2.0), (0xB, 1.9), (0xB, 1.8)])
            good = out[0] == app(name) and out[1] == [] and out[2] == [] and kin_after == 1 and \
                cw == W.B_APPLIED | (W.PEND_VER - 2)
            ok &= good
            table.append((hex(pre), hex(kin), hex(jk), name, 'ok' if good else out))
    check(ok, 'the bounce for every status the stomp comes in (Jump 0xB kinetic 1 -> Jump\'s pre keeps 0x32: no step '
          'jump of the game\'s; JumpAerial 0xC (2), Fall 0xD (0x32), FallAerial 0xE (0x13) -> kinetic 1): u_pend, once '
          'StepJump\'s main has run, sets mode 1 / the kind\'s multiplier and change_kinetic(1) (0x02E7A4DC above: '
          'the step jump), rising after it: nothing more %s' % table)
    jk, out, cw, _k = bounce('dekakuribo', 0, 0xC, 2, [(0xB, 2.0), (0xB, 0.0), (0xB, -0.2), (0xB, -0.4)])
    check(out[0] == app('dekakuribo') and out[1] == app('dekakuribo') and out[2] == [] and out[3] == [] and
          cw & W.B_REDONE,
          'the watch: the speed lost (y <= 0) while still in Jump right after the bounce -> the step jump once more, '
          'then not again %s' % ((out, hex(cw)),))
    jk, out, cw, _k = bounce('dekakuribo', 0, 0xC, 2, [(0xB, 2.0), (0x48, -1.0), (0xB, -1.0)])
    check(out[0] == app('dekakuribo') and out[1] == [] and out[2] == [] and cw == 0,
          'the watch ends when the fighter leaves Jump (a damage status: the bounce is not forced over it) %s'
          % ((out, hex(cw)),))
    jk, out, cw, _k = bounce('dekakuribo', 0, 0xB, 1, [(0xB, 0.0)] * (W.PEND_VER + 3))
    check(sum(1 for o in out if o) == 2,
          'a Jump whose speed never comes (y 0 every update): applied twice in all, never more %s' % out)

    # ---------------------------------------------------------------- the step 2p log's Big Goomba fall
    if len(sys.argv) > 3:
        lines = open(sys.argv[3], errors='replace').read().splitlines()
        hs = [i for i, ln in enumerate(lines) if 'S4N hs k=23' in ln][0]
        near = [ln for ln in lines[:hs] if 'S4N near k=23' in ln][-4:]
        fr = [(f32(re.search(r'fx=(\w+)', ln).group(1)), f32(re.search(r'fy=(\w+)', ln).group(1)),
               f32(re.search(r'ex=(\w+)', ln).group(1)), f32(re.search(r'ey=(\w+)', ln).group(1))) for ln in near]
        m = M(img)
        hw, top, hh = box('dekakuribo')
        rel = [(fx - ex, fy - ey) for fx, fy, ex, ey in fr]
        r = run(m, 'dekakuribo', 0, [(dx, y) for dx, y in rel])
        check(r is not None and r[0] == len(rel) - 1,
              'the step 2p log\'s Big Goomba fall (its last near lines: dx %s, feet above its posture %s) -> stomped '
              'on the same frame as there (box top %.2f) %s' % ([round(a, 2) for a, _ in rel],
                                                               [round(b, 2) for _, b in rel], top, r))
    T.overrun_check()
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
