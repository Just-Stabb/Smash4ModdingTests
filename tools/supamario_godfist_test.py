#!/usr/bin/env python3
"""Super God Fist offline test: the dash attack's MSC (gf_init / gf_update in the compiled supamario.mscsb, run in
rolloff_hold_test's MSC interpreter) and its game script (the attackdash script of the built game.bin, run in a
small ACMD interpreter with a simulated victim), frame by frame, in the scenarios below.

  python3 tools/supamario_godfist_test.py PKG_FIGHTER_DIR      (OUT_DIR/fighter/supamario of the build)

MSC: whiff (ends at GF_WHIFF_END in Wait; in Run when the run flag 0x1300011c is set), hit (the motion rate that
reaches GF_JUMP_TO in one frame, then 1; no cancel before GF_IASA even with the vl cancel frame open; Wait at the
motion's end).
ACMD (the victim: a fighter in player slot 2 that gets up the first frame its controller lets it, from DownWait):
the hold (HOLD_X in front, JUMP_TO .. STRIKE - 1, XV2's lean back), the strike, the flight (XV2's curves: the offsets / spin
each frame, the controller off), lying until DownWait takes over,
landing -> DownWait, held down GF_DOWN frames, then the controller back; a weak hit while down -> it stands up after
the down damage; a launching hit -> released at once; a victim that never lands (off the stage) -> released; a
second God Fist on another fighter while the first is still down -> the first released. Every scenario ends with
no controller left off.

The interpreter's assumptions (the game's, as docs/acmd-extra-commands.md describes them): FRAME waits for the
motion frame, WAIT for that many frames; True(n) skips to n words from itself when the last compare / Hit_Check
was false; Set_Loop(n) ... Goto runs the block n times; Thread_Start's block runs from the next game frame, one
frame a game frame, during the attacker's hitstop too (Flags 1); a status set takes effect the next frame.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_godfist_build as B  # noqa: E402
import rolloff_hold_test as R  # noqa: E402

PROBLEMS = []


def check(name, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        PROBLEMS.append(name)


# ---------------------------------------------------------------- MSC
class MscGame:
    def __init__(self):
        self.frame = 0.0
        self.gf = 0.0
        self.rate = 1.0
        self.status = None
        self.cancel_open = False
        self.run_flag = 0
        self.motion_end = False

    def sys(self, sid, a):
        if sid == 0x17 and len(a) == 2 and a[0] == 0:
            return R.f2i(self.gf if a[1] == B.GF_VAR else 0.0)
        if sid == 0x16:
            if a[0] == 0 and len(a) == 3 and a[2] == B.GF_VAR:
                self.gf = R.i2f(a[1])
            if a[0] == 0x6 and a[-1] == 0x1300011c:
                return self.run_flag
            return 0
        if sid == 0x13 and a == [0x1]:
            return R.f2i(self.frame)
        if sid == 0x12 and len(a) == 2 and a[0] == 0x4:
            self.rate = R.i2f(a[1])
            return 0
        if sid == 0x12 and a == [0x2712]:
            return int(self.motion_end)
        if sid == 0x23 and a == [0x2713]:
            return int(self.cancel_open)
        if sid == 0x18 and len(a) >= 2 and a[0] == 0x3:
            self.status = a[1]
            return 0
        return 0


def msc_vm(path):
    vm = R.VM(path)
    vm.game = MscGame()
    vm.g[11] = vm.func(17).bounds[0]          # func_16's status change: func_17 (StatusModule(3, ...))
    vm.g[18] = 0                              # on the ground
    return vm


def msc_tests(path):
    init, loop = None, None
    vm = msc_vm(path)
    # func_272 is the AttackDash init (it plays motion 0x56), func_273 its loop
    init, loop = vm.func(272), vm.func(273)
    # whiff
    for run_flag, want in ((0, 0), (1, 0x12)):
        vm = msc_vm(path)
        vm.game.run_flag = run_flag
        vm.call(init)
        ended = None
        for f in range(0, int(B.WHIFF_END) + 6):
            vm.game.frame = float(f)
            vm.call(loop)
            if vm.game.status is not None:
                ended = (f, vm.game.status)
                break
        check('MSC whiff (run flag %d): ends at frame %d in status 0x%X' % (run_flag, B.WHIFF_END, want), ended,
              (int(B.WHIFF_END), want))
    # hit: gf set at the hit check (the game script, PUNCH_END), the vl cancel window open from frame 39
    vm = msc_vm(path)
    g = vm.game
    vm.call(init)
    check('MSC init: gf 0', g.gf, 0.0)
    trace = []
    f = 0.0
    last = float(B.anim.FRAMES - 1)
    while f <= last and g.status is None:
        g.frame = f
        g.cancel_open = f >= 39
        g.motion_end = f >= last
        if f >= B.PUNCH_END:
            g.gf = 1.0
        g.rate = None
        vm.call(loop)
        trace.append((f, g.rate))
        f = f + (g.rate if g.rate is not None else (trace and [r for _f, r in trace if r is not None][-1:] or [1.0])[0])
    rates = [(fr, r) for fr, r in trace if r is not None]
    h = float(B.PUNCH_END)
    check('MSC hit: the jump (frame %d, rate %d), then rate 1 at frame %d' % (h, B.JUMP_TO - h, B.JUMP_TO), rates,
          [(h, float(B.JUMP_TO - h)), (float(B.JUMP_TO), 1.0)])
    check('MSC hit: no status change before the motion end (cancel window ignored)', (trace[-1][0], g.status),
          (last, 0))
    # the God Fist's cancel frame: acting (func_39) only from GF_IASA (a stub: every frame it is asked, it acts)
    vm = msc_vm(path)
    g = vm.game
    vm.call(init)
    asked = []
    f39 = vm.func(39)
    orig = vm.call

    def call(script, args=(), orig=orig):
        if script is f39:
            asked.append(g.frame)
            return 0
        return orig(script, args)
    vm.call = call
    for fr in range(B.PUNCH_END, int(last)):
        g.gf = 1.0
        g.frame = float(fr) if fr == B.PUNCH_END else float(B.JUMP_TO + fr - B.PUNCH_END - 1)
        vm.call(loop)
    check('MSC hit: no acting before GF_IASA (%d)' % B.IASA, min(asked) if asked else None, B.IASA)


# ---------------------------------------------------------------- ACMD
VAR_IDS = {v for _n, v, _s in B.VARS}


class Victim:
    def __init__(self, slot=2):
        self.slot = slot
        self.status = 0x45            # Damage (ground), after the dash punch
        self.pending = None
        self.situation = 0
        self.input_off = 0.0
        self.offx = None              # last LASTHIT offsets written
        self.offy = None
        self.ground = None
        self.rot = (0.0, 0.0, 0.0)
        self.trace = []               # (offset x, offset y, rotation X, status) at every Rotation_Set
        self.log = []
        self.hit_at = {}              # frame -> 'weak' / 'launch'
        self.never_lands = False
        self.fall = 0

    def frame(self, n):
        if self.pending is not None:
            self.status, self.pending = self.pending, None
            if self.status == 0x57:
                self.dmg = 10
        kind = self.hit_at.get(n)
        if kind == 'weak' and self.status in (0x50, 0x51):
            self.status, self.dmg = 0x57, 10
        elif kind == 'launch':
            self.status = 0x47
        if self.status == 0x57:
            self.dmg -= 1
            if self.dmg <= 0:
                self.status = 0x51
        elif self.status in (0x50, 0x51) and not self.input_off:
            self.status = 0x54            # gets up the first frame it can
        if self.ground == 5 and self.situation != 0 and not self.never_lands:
            self.fall += 1
            if self.fall >= 2:
                self.situation = 0
        elif self.ground == 0:
            self.situation, self.fall = 2, 0


class Runner:
    def __init__(self, cmds, start, game_frames):
        self.cmds, self.k = cmds, start
        self.wait_until = None
        self.loops = []
        self.cond = False
        self.done = False
        self.thread_frames = game_frames      # True: FRAME counts game frames from the start
        self.t = 0


class Acmd:
    def __init__(self, cmds, victim, slot2=True):
        self.cmds = cmds
        self.word = []
        w = 0
        for c in cmds:
            self.word.append(w)
            w += acmd.INFO[c.ident]['size']
        self.at_word = {w: k for k, w in enumerate(self.word)}
        self.vars = {}
        self.v = victim
        self.threads = {}
        self.new_threads = []
        self.hits = set()          # frames whose hitboxes connect with the victim's body
        self.self_hit = False

    def target(self, t):
        return self.v if t == 2 or (t >= 3 and t - 2 == self.v.slot) else None

    def jump(self, r, k, off):
        off = int(off)
        off = off - (1 << 32) if off >= 1 << 31 else off
        r.k = self.at_word[self.word[k] + off]

    def step(self, r, frame):
        """run r until it waits; frame: the motion frame (main) or None (thread)"""
        while not r.done:
            if r.wait_until is not None:
                now = r.t if frame is None else frame
                if now < r.wait_until:
                    return
                r.wait_until = None
            c = self.cmds[r.k]
            k = r.k
            r.k += 1
            n, p = c.name, c.params
            if c.ident == acmd.END:
                r.done = True
            elif n == 'FRAME':
                r.wait_until = p[0]
            elif n == 'WAIT':
                r.wait_until = (r.t if frame is None else frame) + p[0]
            elif n == 'Float_Var_Compare':
                a, b = self.vars.get(p[0], 0.0), p[2]
                r.cond = {0: a == b, 1: a != b, 2: a <= b, 3: a >= b, 4: a < b, 5: a > b}[p[1]]
            elif n == 'Hit_Check':
                r.cond = self.self_hit
            elif n == 'True':
                if not r.cond:
                    self.jump(r, k, p[0])
            elif n == 'Set_Loop':
                r.loops.append([r.k, p[0]])
            elif n == 'Goto':
                lp = r.loops[-1]
                lp[1] -= 1
                if lp[1] > 0:
                    self.jump(r, k, p[0])
                else:
                    r.loops.pop()
            elif n == 'Thread_Start':
                self.new_threads.append((p[1], Runner(self.cmds, r.k, True)))
                self.jump(r, k, p[0])
            elif n == 'New_Var':
                if p[3] == 1 or p[0] not in self.vars:
                    self.vars[p[0]] = p[2]
            elif n == 'SET_FLOAT':
                self.setvar(p[1], p[0])
            elif n == 'SUB_FLOAT_2':
                self.vars[p[0]] = self.vars.get(p[0], 0.0) - self.vars.get(p[1], 0.0)
            elif n == 'Hit_Reset':
                self.self_hit = False
            elif n in ('Hitbox', 'Extra_Special_Hitbox'):
                self.hitbox_frame = frame
            elif n == 'Target_Slot_Get':
                tv = self.target(p[0])
                self.vars[p[1]] = float(tv.slot if tv else 0)
            else:
                tv = self.target(p[0]) if p else None
                if n == 'Status_Set' and tv:
                    tv.pending = p[1]
                    tv.log.append(('status', p[1]))
                elif n == 'Status_Get':
                    self.vars[p[1]] = float(tv.status if tv else 0)
                elif n == 'Input_Set' and tv and p[1] == 21:
                    tv.input_off = p[2]
                    tv.log.append(('input_off', p[2]))
                elif n == 'Input_Get':
                    self.vars[p[2]] = float(tv.situation if tv and p[1] == 22 else 0)
                elif n == 'Rotation_Set' and tv:
                    tv.rot = tuple(p[1:4])
                    tv.trace.append((tv.offx, tv.offy, p[1], tv.status))
                elif n in ('Hitstun_Set', 'Hitstop_Set') and tv:
                    tv.log.append((n, p[1]))

    def setvar(self, var, val):
        if var == B.LH_OFFX:
            self.v.offx = val
        elif var == B.LH_OFFY:
            self.v.offy = val
        elif var == B.LH_GROUND:
            self.v.ground = val
        else:
            self.vars[var] = val


def run_move(script, victim, hit=True, strike_hits=True, frames=400, second=None):
    """the move from frame 0; hit: the punch connects (frames 7-10); returns (acmd, per-frame records)"""
    a = Acmd(script, victim)
    main = Runner(script, 0, False)
    rec = []
    frame, freeze, jumped, struck = 0.0, 0, False, False
    for g in range(frames):
        # main script (frozen while in hitstop)
        if freeze > 0:
            freeze -= 1
        elif not main.done:
            a.step(main, frame)
            if hit and B.PUNCH <= frame < B.PUNCH_END:
                a.self_hit = True
            if strike_hits and frame == B.STRIKE and a.vars.get(B.GF_VAR) == 1.0 and not struck:
                struck = True
                a.self_hit = True
                freeze = B.STRIKE_FREEZE
            # the MSC's jump (gf_update): from the frame after gf is set, one frame to GF_JUMP_TO
            if a.vars.get(B.GF_VAR) == 1.0 and not jumped and frame < B.JUMP_TO:
                jumped = True
                frame = float(B.JUMP_TO)
                a.step(main, frame)
            elif freeze == 0:
                frame += 1.0
                if a.vars.get(B.GF_VAR, 0.0) == 0.0 and frame > B.WHIFF_END:
                    main.done = True
        for tid, r in a.new_threads:
            a.threads[tid] = r
        a.new_threads = []
        for tid, r in list(a.threads.items()):
            a.step(r, None)
            r.t += 1
            if r.done:
                del a.threads[tid]
        victim.frame(g)
        rec.append((g, frame, victim.offx, victim.offy, victim.rot[0], victim.status, victim.input_off,
                    victim.situation))
        if second and g == second[0]:
            return a, rec
    return a, rec


def acmd_tests(game_bin):
    f = acmd.ACMDFile.load(game_bin)
    script = f.script('attackdash')
    # whiff
    v = Victim()
    a, rec = run_move(script, v, hit=False, frames=60)
    check('ACMD whiff: gf stays 0, nothing done to anyone', (a.vars.get(B.GF_VAR), v.log, a.threads), (0.0, [], {}))
    # the full God Fist, nothing else happening
    v = Victim()
    a, rec = run_move(script, v)
    held = [r for r in rec if B.JUMP_TO <= r[1] < B.STRIKE]
    check('hold: the victim %g in front on the ground while held' % B.HOLD_X, {(r[2], r[3]) for r in held}, {(B.HOLD_X, 0.0)})
    n_hold = B.STRIKE - B.JUMP_TO
    tr = v.trace
    want_hold = [(B.HOLD_X, 0.0, -B.hold_lean(k, n_hold)) for k in range(n_hold)]
    check('hold: XV2\'s lean back (#179 0-40: %.0f -> %.0f degrees)' % (-want_hold[0][2], -want_hold[-1][2]),
          all(abs(a[2] - b[2]) < 1e-3 and a[:2] == b[:2] for a, b in zip(tr[:n_hold], want_hold)), True)
    flight = tr[n_hold:n_hold + B.GF_FLIGHT]
    want = [B.flight_offset(k) for k in range(1, B.GF_FLIGHT + 1)]
    ok = len(flight) == len(want) and all(abs(x - wx) < 1e-3 and abs(y - wy) < 1e-3 and abs(r_ - wa) < 1e-2
                                          for (x, y, r_, _st), (wx, wy, wa) in zip(flight, want))
    check('flight: %d frames of offsets / spin as flight_offset (XV2 #179 / #96, less his own travel)' % B.GF_FLIGHT,
          ok, True)
    check('flight: ends %g in front (feet), lying (%g degrees)' % (want[-1][0], want[-1][2]),
          (round(flight[-1][0], 3), flight[-1][2]), (round(want[-1][0], 3), want[-1][2]))
    turned = abs(want[-1][2] - (-B.hold_lean(n_hold - 1, n_hold)))
    check('flight: turns %.0f degrees backward (XV2 935 x 0.8)' % turned, 700 < turned < 800, True)
    after = tr[n_hold + B.GF_FLIGHT:]
    check('kept lying until DownWait, then upright', [r[2] for r in after if r[3] != 0x50][:1] == [want[-1][2]]
          and next((r for r in after if r[2] == 0.0), (0, 0, 0, None))[3] == 0x50, True)
    check('rotation back to 0 at the end', v.rot[0], 0.0)
    lock_on = next(r[0] for r in rec if r[6] == 1.0)
    launch = next(r[0] for r in rec if r[1] > B.STRIKE)
    check('controller off from the launch (the thread\'s first frame)', lock_on <= launch + 1, True)
    down = [r for r in rec if r[5] == 0x50]
    check('lands, DownWait (0x50)', bool(down), True)
    first_down = down[0][0]
    up = next((r[0] for r in rec if r[5] == 0x54), None)
    check('held down %d frames, then gets up (DownStand)' % B.GF_DOWN, up is not None and
          B.GF_DOWN - 2 <= up - first_down <= B.GF_DOWN + 2, True)
    check('no getup before the end (status stays 0x50)', all(r[5] == 0x50 for r in rec if first_down <= r[0] < up),
          True)
    check('controller back at the end', (v.input_off, a.vars.get(B.V_LOCK)), (0.0, 0.0))
    # a weak hit while down (20 frames in): DownDamage, then it stands
    v = Victim()
    a0, rec0 = run_move(script, v, frames=200)
    land = next(r[0] for r in rec0 if r[5] == 0x50)
    v = Victim()
    v.hit_at = {land + 20: 'weak'}
    a, rec = run_move(script, v)
    dd = [r[0] for r in rec if r[5] == 0x57]
    stood = next((r[0] for r in rec if r[5] == 0x54), None)
    check('weak hit while down: DownDamage, then DownStand right after it',
          bool(dd) and stood is not None and dd[-1] < stood <= dd[-1] + 3, True)
    check('weak hit: stood well before the %d frames' % B.GF_DOWN, stood - land < B.GF_DOWN, True)
    check('weak hit: Status_Set DownStand (0x54) and controller back', (('status', 0x54) in v.log, v.input_off),
          (True, 0.0))
    # a launching hit while down
    v = Victim()
    v.hit_at = {land + 15: 'launch'}
    a, rec = run_move(script, v)
    rel = next((r[0] for r in rec if r[0] > land + 15 and r[6] == 0.0), None)
    check('launching hit while down: controller back at once', rel is not None and rel <= land + 17, True)
    check('launching hit: never stood up by the move', ('status', 0x54) in v.log, False)
    # never lands (off the stage)
    v = Victim()
    v.never_lands = True
    a, rec = run_move(script, v)
    check('never lands: no DownWait, controller back', (('status', 0x50) in v.log, v.input_off), (False, 0.0))
    # the dash punch on a shield / no catch: strike never happens
    v = Victim()
    a, rec = run_move(script, v, hit=False, frames=120)
    check('no catch: no hold / flight (no rotation)', v.trace, [])
    # a second God Fist (on another fighter, slot 3) while the first victim is still held down: released at the catch
    v = Victim()
    a, rec = run_move(script, v, frames=land + 10)
    check('first victim locked before the second move', v.input_off, 1.0)
    vars_ = dict(a.vars)
    v2 = Victim(slot=3)
    a2 = Acmd(script, v2)
    a2.vars = vars_
    # the second move's catch releases slot 2 (gf_lock): run its main script to frame 12 with the old victim reachable
    main = Runner(script, 0, False)
    a2.self_hit = True

    def target(t, a2=a2):
        if t == 2 or t == 5:
            return v2
        if t == 4:
            return v
        return None
    a2.target = target
    for fr in range(0, B.PUNCH_END + 1):
        a2.step(main, float(fr))
    check('second God Fist: the first victim gets its controller back', v.input_off, 0.0)


def main():
    a = sys.argv[1:]
    if len(a) != 1:
        sys.exit(__doc__)
    d = a[0]
    # his TransN by motion frame (the flight offsets take his travel off): from the built AttackDash
    import omo
    e = dict(omo.pac_read(os.path.join(d, 'motion', 'body', 'main.pac')))
    o = omo.Omo(e['FitMarioBodyMainC00AttackDash.omo'])
    trans = o.nodes[0][1]                       # TransN: the first node (vbn order)
    B.ROOT_Z[:] = [o.sample(trans, f)[0][2] for f in range(o.frames)]
    msc_tests(os.path.join(d, 'script', 'msc', 'supamario.mscsb'))
    acmd_tests(os.path.join(d, 'script', 'animcmd', 'body', 'game.bin'))
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
