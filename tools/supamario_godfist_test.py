#!/usr/bin/env python3
"""Super God Fist offline test: the dash attack's MSC (gf_init / gf_update in the compiled supamario.mscsb, run in
rolloff_hold_test's MSC interpreter) and its game script (the attackdash script of the built game.bin, run in a
small ACMD interpreter with a simulated victim), frame by frame, in the scenarios below.

  python3 tools/supamario_godfist_test.py PKG_FIGHTER_DIR [--all-models]   (OUT_DIR/fighter/supamario of the build)

v4: the interpreter models hitboxes, Part hit records, Hit_Reset / Hit_Log_Clear, his hitstop and a status change
(the script and hitboxes gone, the threads on); Acmd.DEFER (the kinds of a hit reach Hit_Check only after the next
unfrozen frame's script: v3's clip) and Acmd.BLOCK (a Part record for the whole status) are the game's open rules,
--all-models runs every combination. On v3's build it reproduces the in-game report (the strike connects, no
launch, the hold's lean left on the victim); v4 adds the hold's interruptions, the strike not connecting, a status
change mid-flight, a second God Fist while the first victim lies / is held down, rotation 0 at every end.

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
PREFIX = ['']


def check(name, got, want):
    name = PREFIX[0] + name
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
WAIT_STATUS = 0x0
FALL = 0x1A                    # (any status out of the down ones)
DAMAGE_STATUSES = (0x45, 0x47, 0x4C)


class Victim:
    def __init__(self, slot=2):
        self.slot = slot
        self.status = WAIT_STATUS
        self.pending = None
        self.situation = 0
        self.input_off = 0.0
        self.offx = None              # last LASTHIT offsets written
        self.offy = None
        self.ground = None
        self.rot = (0.0, 0.0, 0.0)    # PostureModule rotation: kept until set again (no status resets it: v3 in game)
        self.trace = []               # (offset x, offset y, rotation X, status) at every Rotation_Set
        self.log = []
        self.hit_at = {}              # frame -> 'weak' / 'launch'
        self.never_lands = False
        self.fall = 0
        self.hittable = lambda motion_frame: True     # its hurtbox there (False: intangible / out of reach)
        self.hitstun = 0
        self.bound = 0
        self.stop = 0                 # hitstop frames left (frozen: its status doesn't run)
        self.push = None              # the PUSH (energy 4 speed) written
        self.push_log = []            # (game frame, its status, value)
        self.hits_taken = []          # (game frame, part)

    def frame(self, n):
        frozen = self.stop > 0
        if frozen:
            self.stop -= 1
        if self.pending is not None:
            self.status, self.pending = self.pending, None
            if self.status == 0x57:
                self.dmg = 10
        kind = self.hit_at.get(n)
        if kind == 'weak' and self.status in (0x50, 0x51):
            self.status, self.dmg = 0x57, 10
        elif kind == 'launch':
            self.status = 0x47
            self.hitstun = 30
        if self.status == 0x57:
            self.dmg -= 1
            if self.dmg <= 0:
                self.status = 0x51
        elif self.status in (0x50, 0x51) and not self.input_off:
            self.status = 0x54            # gets up the first frame it can
        elif self.status == 0x45 and self.situation != 0 and not frozen:
            self.status = FALL                # a ground Damage status in the air, not frozen: Fall (v6's log)
        elif self.status in DAMAGE_STATUSES:
            self.hitstun -= 1
            if self.hitstun <= 0:             # its hitstun over (the game: Wait, Fall...): the rotation stays
                self.status = 0x4C if self.status == 0x47 and self.situation != 0 else WAIT_STATUS
        if self.status in (0x50, 0x51) and self.situation != 0:
            self.status = FALL            # DownWait in the air: its loop (func_963) goes to Fall
        if self.status == 0x4D:
            self.bound -= 1
            if self.bound <= 0:
                self.status = 0x50        # DownBound's motion over: DownWait
        if self.ground == 5 and self.situation != 0 and not self.never_lands:
            self.fall += 1
            if self.fall >= 3:
                self.situation = 0
                if self.status in (0x47, 0x4C):   # tumbling onto the ground, no tech: DownBound
                    self.status, self.bound = 0x4D, 12
        elif self.ground == 0:
            self.situation, self.fall = 2, 0

    def lying(self):
        return B.DOWN_LO <= self.status <= B.DOWN_HI or self.status == B.DOWN_FURAFURA

    def hit(self, g, part, hitstun):
        self.hits_taken.append((g, part))
        if self.lying():
            self.status, self.dmg = 0x57, 10      # hit while down: DownDamage
        elif self.status not in DAMAGE_STATUSES:
            self.status = 0x45
        self.hitstun = max(self.hitstun, hitstun)


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
    """the game's rules modelled (docs/native-notes.md "Collision records", acmd_ext_cave.py): a hitbox hits a
    fighter once per Part: the Part's hit record keeps it for the rest of the status (Remove_All_Hitboxes and
    Hit_Reset keep it; Hit_Log_Clear(Part) clears it; rehit 0); Hit_Check / Hit_Get read the kinds hit since the
    start (cleared by Hit_Reset) or this frame (AttackModule +0xC8 / +0xC4, new records only: 0x02C09C0C); threads
    outlive status changes (dropped only at the object's set-up)"""

    # the game's rules the in-game tests left open (every combination is run on v4):
    # DEFER: a hit's kinds reach Hit_Check / Hit_Get only after the attacker's next unfrozen frame's script (the
    #   v3 clip: the strike dealt its 11%, yet the Hit_Check one frame after its freeze didn't see it)
    # BLOCK: a Part's hit record keeps a fighter it hit from being hit again by that Part for the whole status
    #   (docs/native-notes.md; not what the v3 clip shows: the strike on the punch's Part 0 connected); not BLOCK:
    #   the record holds while the Part's hitboxes are out, a new hitbox after Remove_All_Hitboxes starts a new one
    # T2_THREAD: target 2 (the last fighter hit) found from a thread
    # THREADS: a Thread_Start'ed block runs (v4's clip: nothing its flight thread did reached the victim; the
    #   unicorn tests run the cave's threads on a weapon, never in game: False is the in-game observation)
    DEFER, BLOCK, T2_THREAD, THREADS = True, False, True, False
    # NO_DOWN: a hitbox with Ground/Air bit 31 misses a fighter lying down (0x02C0E7CC: its target class mask 1, not
    #   3); False: the game ignored it (the catch's own status guard is all that's left)
    NO_DOWN = True

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
        self.active = {}           # hitbox ID -> (Part, self hitstop)
        self.records = {}          # Part -> set of victim slots
        self.bits_start = 0
        self.bits_frame = 0
        self.pending_bits = 0
        self.stale = set()         # Parts whose hitboxes were all removed (not BLOCK: their next hitbox, a new record)
        self.in_thread = False
        self.my_status = B.STATUS_ATTACK_DASH
        self.motion_frame = 0.0
        self.g = 0
        self.diag = []             # (k, value) written to the diag IDs

    def target(self, t, thread=False):
        if t == 2 and thread and not self.T2_THREAD:
            return None
        return self.v if t == 2 or (t >= 3 and t - 2 == self.v.slot) else None

    def slot_var(self, var):
        """(target, quantity) of a combat / hit variable (0x0F000040-0x0F0000F7), else None"""
        i = var - 0x0F000000
        if 0x40 <= i < 0x98:
            return (i - 0x40) // 8, (i - 0x40) % 8
        if 0xA0 <= i < 0xF8:
            return (i - 0xA0) // 8, 8 + (i - 0xA0) % 8
        return None

    def apply_bits(self):
        self.bits_frame = self.pending_bits
        self.bits_start |= self.pending_bits
        self.pending_bits = 0

    def jump(self, r, k, off):
        off = int(off)
        off = off - (1 << 32) if off >= 1 << 31 else off
        r.k = self.at_word[self.word[k] + off]

    def collide(self, g):
        """the frame's collision: each live hitbox against the victim, once per Part record; -> self hitstop"""
        freeze = 0
        for hid, (part, stop, vstop, sit) in sorted(self.active.items()):
            rec = self.records.setdefault(part, set())
            if self.v.slot in rec or not self.v.hittable(self.motion_frame):
                continue
            if self.NO_DOWN and sit & B.NO_DOWN and self.v.lying():
                continue
            rec.add(self.v.slot)
            self.pending_bits |= 2
            self.v.hit(g, part, 20)
            self.v.stop = max(self.v.stop, vstop)      # the hit's freeze on the victim too
            freeze = max(freeze, stop)
            break                           # one hit of an attack a frame
        if not self.DEFER:
            self.apply_bits()
        return freeze

    def step(self, r, frame):
        """run r until it waits; frame: the motion frame (main) or None (thread)"""
        self.in_thread = frame is None
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
                a, b = self.getvar(p[0]), p[2]
                r.cond = {0: a == b, 1: a != b, 2: a <= b, 3: a >= b, 4: a < b, 5: a > b}[p[1]]
            elif n == 'Hit_Check':
                bits = self.bits_start if p[1] == 0 else self.bits_frame
                r.cond = bool(bits & (p[2] or 0x7F))
            elif n == 'Hit_Get':
                self.vars[p[2]] = float(self.bits_start if p[1] == 0 else self.bits_frame)
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
                if self.THREADS:
                    self.new_threads.append((p[1], Runner(self.cmds, r.k, True)))
                self.jump(r, k, p[0])
            elif n == 'Thread_Stop':
                self.threads.pop(p[0], None)
                self.new_threads = [(i, t) for i, t in self.new_threads if i != p[0]]
            elif n == 'New_Var':
                if p[3] == 1 or p[0] not in self.vars:
                    self.vars[p[0]] = p[2]
            elif n == 'SET_FLOAT':
                self.setvar(p[1], p[0])
            elif n == 'SUB_FLOAT_2':
                self.setvar(p[0], self.getvar(p[0]) - self.getvar(p[1]))
            elif n == 'Hit_Reset':
                self.bits_start = 0
            elif n == 'Hit_Log_Clear':
                if p[0] == -1 or p[0] == 0xFFFFFFFF:
                    self.records.clear()
                else:
                    self.records.pop(p[0], None)
            elif n in ('Hitbox', 'Extra_Special_Hitbox'):
                d = dict(zip(acmd.INFO[c.ident]['syntax'], p))
                self.active[d['ID']] = (d['Part'], d.get('SelfHitstopFrames', 0), d.get('HitstopFrames', 0),
                                        d['Ground/Air'])
                if d['Part'] in self.stale and not self.BLOCK:
                    self.stale.discard(d['Part'])
                    self.records.pop(d['Part'], None)
            elif n == 'Remove_All_Hitboxes':
                self.active.clear()
                self.stale = set(self.records)
            elif n == 'Target_Slot_Get':
                tv = self.target(p[0], frame is None)
                self.vars[p[1]] = float(tv.slot if tv else 0)
            elif n == 'Status_Get' and p[0] == 0:
                self.vars[p[1]] = float(self.my_status)
            elif n == 'Motion_Get' and p[0] == 0:
                self.vars[p[2]] = float(self.motion_frame if p[1] == 1 else 0)
            else:
                tv = self.target(p[0], frame is None) if p else None
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
                elif n == 'Rotation_Get':
                    self.vars[p[2]] = float(tv.rot[p[1]] if tv else 0)
                elif n == 'Stage_Collision_Set' and tv:
                    tv.ground = p[1]
                elif n == 'Hitstun_Set' and tv:
                    tv.hitstun = p[1]
                    tv.log.append((n, p[1]))
                elif n == 'Hitstop_Set' and tv:
                    tv.stop = max(tv.stop, int(p[1]))
                    tv.log.append((n, p[1]))

    FACING = 1.0

    def getvar(self, var):
        if B.DIAG_BASE <= var < B.DIAG_BASE + 16:
            return 0.0                      # the diag IDs read 0
        if var == B.SELF_FACING:
            return self.FACING
        tq = self.slot_var(var)
        if tq and tq[1] == 8 + 2:               # a target's status
            tv = self.target(tq[0], self.in_thread)
            return float(tv.status) if tv else 0.0
        return self.vars.get(var, 0.0)

    def setvar(self, var, val):
        tq = self.slot_var(var)
        tv = self.target(tq[0], self.in_thread) if tq else None
        if tq and tq[1] == 5:
            if tv:
                tv.offx = val
        elif tq and tq[1] == 6:
            if tv:
                tv.offy = val
        elif tq and tq[1] == 8 + 6:
            if tv:
                tv.ground = val
        elif tq and tq[1] == 8 + 7:
            if tv:
                tv.push = val
                tv.push_log.append((self.g, tv.status, val))
        elif tq:
            pass
        elif B.DIAG_BASE <= var < B.DIAG_BASE + 16:
            self.diag.append((var - B.DIAG_BASE, val))
        else:
            self.vars[var] = val


class MscTick:
    """the compiled gf_tick (the MSC's per-frame hook calls it every frame, every status), run on the game
    script's New_Vars (a.vars) and the victim / his status through the variables it reads and writes"""
    PATH = None

    def __init__(self, a):
        self.a = a
        self.vm = R.VM(self.PATH)
        self.vm.game = self
        self.fn = self.vm.func(len(self.vm.m.scripts) - 1)     # gf_tick: the last function

    def var(self, i):
        a, v = self.a, self.a.v
        if i == 0x0F0000A2:
            return float(a.my_status)
        tq = a.slot_var(i)
        if tq and tq[0] - 2 == v.slot and tq[1] == 8 + 2:
            return float(v.status)
        return a.getvar(i)

    def sys(self, sid, args):
        a, v = self.a, self.a.v
        if sid == 0x17 and len(args) == 2 and args[0] == 0:
            return R.f2i(self.var(args[1]))
        if sid == 0x16 and len(args) == 2 and args[0] == 6:
            return int(self.var(args[1]))
        if sid == 0x16 and len(args) == 3 and args[0] == 0:
            val, i = R.i2f(args[1]), args[2]
            tq = a.slot_var(i)
            if tq and tq[0] - 2 == v.slot and tq[1] == 8 + 2:
                v.pending = int(val)
                v.log.append(('status', int(val)))
            elif 0x0F000100 <= i < 0x0F000260 and (i - 0x0F000100) % 0x20 == 21:
                if (i - 0x0F000100) // 0x20 - 2 == v.slot:
                    v.input_off = val
                    v.log.append(('input_off', val))
            else:
                a.setvar(i, val)
            return 0
        return 0

    def tick(self):
        self.vm.call(self.fn)


def run_move(script, victim, hit=True, frames=400, second=None, interrupt=None, acm=None):
    """the move from frame 0, frame by frame as the game: the main script at his motion frame (frozen in his
    hitstop), the MSC's jump to JUMP_TO the frame after gf is 1, the threads (Flags 1: in hitlag too), then the
    frame's collision (hitboxes vs the victim, the Part records), then the victim's frame. hit: the victim can be
    hit by the punch (False: a whiff); interrupt: (game frame, his new status) his status changes there (hit /
    grabbed / ...): the main script and hitboxes gone, the threads go on. -> (Acmd, per-frame records)"""
    a = acm or Acmd(script, victim)
    msc = MscTick(a) if MscTick.PATH else None
    if not hit:
        victim.hittable = lambda f: False
    main = Runner(script, 0, False)
    rec = []
    frame, freeze, jumped = 0.0, 0, False
    for g in range(frames):
        a.g = g
        if interrupt and g == interrupt[0]:
            main.done = True
            a.active.clear()
            a.my_status = interrupt[1]
        # main script (frozen while in hitstop)
        if freeze > 0:
            freeze -= 1
        elif main.done:
            if a.DEFER:
                a.apply_bits()
        else:
            a.motion_frame = frame
            a.step(main, frame)
            # the MSC's jump (gf_update): from the frame after gf is set, one frame to GF_JUMP_TO
            if a.vars.get(B.GF_VAR) == 1.0 and not jumped and frame < B.JUMP_TO:
                jumped = True
                frame = float(B.JUMP_TO)
                a.motion_frame = frame
                a.step(main, frame)
            else:
                frame += 1.0
                if a.vars.get(B.GF_VAR, 0.0) == 0.0 and frame > B.WHIFF_END:
                    main.done = True
                if frame >= B.anim.FRAMES:
                    main.done = True
                    a.active.clear()
                    a.my_status = WAIT_STATUS
            if a.DEFER:
                a.apply_bits()              # the attack's update after the script: the kinds hit reach +0xC8
        for tid, r in a.new_threads:
            a.threads[tid] = r
        a.new_threads = []
        for tid, r in list(a.threads.items()):
            a.step(r, None)
            r.t += 1
            if r.done and a.threads.get(tid) is r:
                del a.threads[tid]
        if msc:
            msc.tick()
        stop = a.collide(g)
        if stop:
            freeze = stop                   # the script resumes with the next frame's commands after the freeze
        victim.frame(g)
        rec.append((g, frame, victim.offx, victim.offy, victim.rot[0], victim.status, victim.input_off,
                    victim.situation, a.vars.get(B.GF_VAR, 0.0), victim.ground))
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
    # (the two bugs of v3 in game: "not launched after the initial hit", "their rotation permanently stuck")
    check('the punch connects (Part 0) and catches: gf 1, the victim\'s slot kept',
          (v.hits_taken[:1] and v.hits_taken[0][1], max(r[8] for r in rec) >= 1, a.vars.get(B.V_SLOT)),
          (0, True, float(v.slot)))
    check('the strike (frame %d) connects (the victim takes it: the v3 clip\'s 4%% + 11%%), and no other hit'
          % B.STRIKE, [p for _g, p in v.hits_taken], [0, B.STRIKE_PART])
    check('launched: gf 2 after the strike', any(r[8] == 2.0 for r in rec), True)
    moved = [r for r in rec if r[8] == 2.0 and r[2] is not None and r[2] > B.HOLD_X + 5]
    check('the victim flies (moved away from the hold: the v4 clip\'s bug: it never moved)', bool(moved), True)
    held = [r for r in rec if B.JUMP_TO <= r[1] < B.STRIKE and r[8] == 1.0]
    check('hold: the victim %g in front on the ground while held' % B.HOLD_X, {(r[2], r[3]) for r in held},
          {(B.HOLD_X, 0.0)})
    n_hold = B.STRIKE - B.JUMP_TO
    tr = v.trace
    want_hold = [(B.HOLD_X, 0.0, -B.hold_lean(k, n_hold)) for k in range(n_hold)]
    check('hold: XV2\'s lean back (#179 0-40: %.0f -> %.0f degrees)' % (-want_hold[0][2], -want_hold[-1][2]),
          all(abs(a_[2] - b_[2]) < 1e-3 and a_[:2] == b_[:2] for a_, b_ in zip(tr[:n_hold], want_hold)), True)
    flight = tr[n_hold:n_hold + B.FLY_N]
    want = [B.flight_v8(k) for k in range(1, B.FLY_N + 1)]
    ok = len(flight) == len(want) and all(abs(x - wx) < 1e-3 and abs(y - wy) < 1e-3 and abs(r_ - wa) < 1e-2
                                          for (x, y, r_, _st), (wx, wy, wa) in zip(flight, want))
    check('flight: %d frames (XV2 #179\'s launch, then %d easing down) of offsets / spin as flight_v8'
          % (B.FLY_N, B.EASE_N), ok, True)
    rates = [want[k + 1][2] - want[k][2] for k in range(len(want) - 1)]
    check('flight: the spin never turns back or jumps (each frame 0 to -60 degrees), ends a whole turn round (-720)',
          (all(-60 < r <= 0 for r in rates[B.GF_LAUNCH - 2:]), want[-1][2]), (True, -720.0))
    check('flight: eased down to the ground (%g) with no jump in height (< 1.5 a frame)' % B.DROP_Y,
          (round(want[-1][1], 3), max(abs(want[k + 1][1] - want[k][1]) for k in range(B.GF_LAUNCH - 1, len(want) - 1))
           < 1.5), (B.DROP_Y, True))
    drop = tr[n_hold + B.FLY_N:n_hold + B.FLY_N + 1]
    check('the hand-off: on the ground, upright (a whole turn from -720: no pop), no hit, no PUSH in the air',
          (drop[:1] and (drop[0][1], drop[0][2]), len(v.hits_taken), v.push_log[:1] and v.push_log[0][1]),
          ((0.0, 0.0), 2, 0x4D))
    slide = [val for _st, s_, val in [(x[1], x[1], x[2]) for x in v.push_log]]
    check('the knockdown\'s slide: %.1f units in all along his facing (XV2 #96\'s 9.44 m), decaying, then 0'
          % B.SLIDE_DIST, (abs(sum(slide) - B.SLIDE_DIST) < 1.0, all(b <= a for a, b in zip(slide, slide[1:])),
                           slide[-1:] == [0.0]), (True, True, True))
    seq = []
    for r in rec:
        if r[5] in (0x4C, 0x4D, 0x50, FALL) and (not seq or seq[-1] != r[5]):
            seq.append(r[5])
    check('the game\'s own knockdown: DamageFall (asked while frozen, never Fall) -> DownBound -> DownWait',
          (seq[:3], [x for x in v.log if x[0] == 'status' and x[1] in (0x4C, 0x4D, 0x50)]),
          ([0x4C, 0x4D, 0x50], [('status', 0x4C)]))
    check('rotation back to 0 at the end', v.rot[0], 0.0)
    Acmd.FACING = -1.0
    vl = Victim()
    run_move(script, vl, frames=B.HANDOFF + 60)
    Acmd.FACING = 1.0
    check('facing left: the slide the other way (PUSH is world X)',
          vl.push_log[:1] and round(vl.push_log[0][2], 3), round(-B.SLIDE_V0, 3))
    lock_on = next((r[0] for r in rec if r[6] == 1.0), None)
    launch = next((r[0] for r in rec if r[8] == 2.0), next(r[0] for r in rec if r[1] > B.STRIKE))
    check('controller off from the launch', lock_on is not None and lock_on <= launch + 1, True)
    down = [r for r in rec if r[5] in (0x4D, 0x50)]
    check('lands, knocked down (DownBound 0x4D, DownWait 0x50)', bool(down), True)
    # (no landing: v3's build; the later scenarios still run, at the frames a landing would have had)
    first_down = down[0][0] if down else launch + B.GF_FLIGHT + 3
    up = next((r[0] for r in rec if r[5] == 0x54), None)
    check('held down %d frames from the knockdown, then gets up (DownStand)' % B.GF_DOWN, up is not None and
          B.GF_DOWN - 2 <= up - first_down <= B.GF_DOWN + 2, True)
    check('no getup before the end (status stays DownBound / DownWait)', up is not None and
          all(r[5] in (0x4D, 0x50) for r in rec if first_down <= r[0] < up), True)
    check('controller back at the end', (v.input_off, a.vars.get(B.V_LOCK)), (0.0, 0.0))
    check('no thread left running at the end', sorted(a.threads), [])
    # a weak hit while down (20 frames in): DownDamage, then it stands
    land = first_down
    v = Victim()
    v.hit_at = {land + 20: 'weak'}
    a, rec = run_move(script, v)
    dd = [r[0] for r in rec if r[5] == 0x57]
    stood = next((r[0] for r in rec if r[5] == 0x54), None)
    check('weak hit while down: DownDamage, then DownStand right after it',
          bool(dd) and stood is not None and dd[-1] < stood <= dd[-1] + 3, True)
    check('weak hit: stood well before the %d frames' % B.GF_DOWN, stood is not None and stood - land < B.GF_DOWN,
          True)
    check('weak hit: Status_Set DownStand (0x54), controller back, upright',
          (('status', 0x54) in v.log, v.input_off, v.rot[0]), (True, 0.0, 0.0))
    # a launching hit while down
    v = Victim()
    v.hit_at = {land + 15: 'launch'}
    a, rec = run_move(script, v)
    rel = next((r[0] for r in rec if r[0] > land + 15 and r[6] == 0.0), None)
    check('launching hit while down: controller back at once, upright', rel is not None and rel <= land + 17
          and v.rot[0] == 0.0, True)
    check('launching hit: never stood up by the move', ('status', 0x54) in v.log, False)
    # never lands (off the stage): still tumbling when the MSC's wait for the down runs out: controller back
    v = Victim()
    v.never_lands = True
    a, rec = run_move(script, v)
    check('never lands (no down within %d frames of the drop): controller back, upright' % B.GF_FALL_WAIT,
          (v.input_off, v.rot[0], v.status in range(0x4D, 0x54)), (0.0, 0.0, False))
    # the dash punch on a shield / no catch: strike never happens
    v = Victim()
    a, rec = run_move(script, v, hit=False, frames=120)
    check('no catch: no hold / flight (no rotation)', v.trace, [])
    # the hold / flight cut short (his status changes: hit, grabbed): controller back at once (the MSC's gf_tick),
    # upright at his next dash attack's first frame (v7: no watchdog thread: the v6 diag log never showed one run)
    hold_g = next(r[0] for r in run_move(script, Victim())[1] if r[1] == B.JUMP_TO + 20)
    launch_g = next((r[0] for r in run_move(script, Victim())[1] if r[8] == 2.0), launch)
    for what, at in (('mid-hold', hold_g), ('mid-flight', launch_g + 10)):
        v = Victim()
        a, rec = run_move(script, v, frames=at + 60, interrupt=(at, 0x48))
        if True:
            check('cut short %s: controller on (MSC)' % what, v.input_off, 0.0)
            # his next dash attack (on nobody): frame 0 turns the earlier victim upright
            a.active.clear()
            a.records, a.bits_start, a.my_status = {}, 0, B.STATUS_ATTACK_DASH
            v.hittable = lambda f: False
            a, rec = run_move(script, v, frames=3, acm=a)
            check('cut short %s: upright, stage collision back at his next dash attack' % what,
                  (v.rot[0], v.ground), (0.0, 5))
    v = Victim()
    a = Acmd(script, v)
    a0, rec = run_move(script, v, frames=hold_g + 1, acm=a)
    v.hittable = lambda f: False
    a.active.clear()
    a.records, a.bits_start = {}, 0         # a new status: a new attack
    a, rec = run_move(script, v, frames=40, acm=a)
    check('a new dash attack mid-hold: the old victim upright, stage collision back, controller on',
          (v.rot[0], v.ground, v.input_off), (0.0, 5, 0.0))
    # the strike doesn't connect (the victim intangible at it): the hold is a throw, launched all the same
    v = Victim()
    v.hittable = lambda f: f != B.STRIKE
    a, rec = run_move(script, v)
    check('strike not connecting: still launched, downed, upright at the end, controller back',
          (any(r[8] == 2.0 for r in rec), any(r[5] == 0x50 for r in rec), v.rot[0], v.input_off),
          (True, True, 0.0, 0.0))
    # a second God Fist (on another fighter, slot 3) while the first victim is still held down
    v = Victim()
    a, rec = run_move(script, v, frames=land + 10)
    check('first victim held down (controller off) before the second move', v.input_off, 1.0)
    v2 = Victim(slot=3)
    a2 = Acmd(script, v2)
    a2.vars = dict(a.vars)
    a2.records = {}

    def target(t, thread=False, v=v, v2=v2):
        if t == 2 or t == 5:
            return v2
        if t == 4:
            return v
        return None
    a2.target = target
    main = Runner(script, 0, False)
    a2.bits_start = 2
    for fr in range(0, B.PUNCH_END + 1):
        a2.motion_frame = float(fr)
        a2.step(main, float(fr))
    check('second God Fist: the first victim\'s controller back, the MSC lets it go (gf_phase 0), upright',
          (v.input_off, a2.vars.get(B.V_PHASE), v.rot[0]), (0.0, 0.0, 0.0))
    # v9: a fighter lying down is neither hit nor caught
    punch = [c for c in script if c.name in ('Hitbox', 'Extra_Special_Hitbox')
             and dict(zip(acmd.INFO[c.ident]['syntax'], c.params))['Part'] == 0]
    check('the punch\'s hitboxes miss a fighter lying down (Ground/Air bit 31, as vanilla Diddy\'s 0x80000003)',
          sorted(set(dict(zip(acmd.INFO[c.ident]['syntax'], c.params))['Ground/Air'] for c in punch)),
          [B.PUNCH_SITUATION])
    for st, name in ((0x50, 'DownWait'), (0x4D, 'DownBound'), (0x54, 'DownStand'), (0x57, 'DownDamage')):
        for no_down in (True, False):
            Acmd.NO_DOWN = no_down
            v = Victim()
            v.status, v.input_off, v.dmg = st, 1.0, 99      # held down (as the MSC holds one)
            v.frame = lambda n: None                         # it stays as it is
            a, rec = run_move(script, v, frames=60)
            got = (a.vars.get(B.GF_VAR, 0.0), any(r[1] >= B.JUMP_TO for r in rec), v.rot, v.offx)
            if no_down:
                check('lying (%s): not hit, no catch: a whiff' % name, (len(v.hits_taken),) + got,
                      (0, 0.0, False, (0.0, 0.0, 0.0), None))
            else:
                check('lying (%s), the flag ignored by the game: hit, but not caught (the status guard)' % name,
                      (len(v.hits_taken) > 0,) + got, (True, 0.0, False, (0.0, 0.0, 0.0), None))
    Acmd.NO_DOWN = True
    # the victim of a God Fist, held down by the MSC, under a second God Fist: missed, still held, then gets up
    v = Victim()
    a, rec = run_move(script, v, frames=land + 10)
    hits = len(v.hits_taken)
    a2, rec2 = run_move(script, v, frames=120, acm=Acmd(script, v))
    check('a God Fist on its own downed victim: missed (no hit), no catch',
          (len(v.hits_taken) - hits, a2.vars.get(B.GF_VAR, 0.0)), (0, 0.0))


def facing_tests(body_dir):
    """every effect of the move looks the same, mirrored left-right, when he faces the other way. Only bone 0 (TopN:
    Z forward along his facing, Y up, X across = depth, in both facings: Mario's own forward smash fire is Bone 0,
    Y 7, Z 15) has axes that are the same on screen both ways: an effect there may sit at a height and a distance
    ahead (no X: depth) and turn only about Y by 0 / 180. A body bone's own axes are not (v5: on RHandN, whose +Y
    points down at the punch, turned Y -90, the model came out upside down with one facing: the user's v5 clip),
    so an effect on any other bone gets no offset and no turn (it sits on the bone, camera-facing particles)."""
    bad = []
    for part in ('effect', 'game'):
        for c in acmd.ACMDFile.load(os.path.join(body_dir, part + '.bin')).script('attackdash'):
            if c.name not in ('Graphic_Effect', 'External_Graphic'):
                continue
            d = dict(zip(acmd.INFO[c.ident]['syntax'], c.params))
            if d['Bone'] == 0:
                ok = d['X'] == 0 and d['XRot'] == 0 and d['ZRot'] == 0 and abs(d['YRot']) in (0, 180)
            else:
                ok = all(d[k] == 0 for k in ('X', 'Y', 'Z', 'XRot', 'YRot', 'ZRot'))
            if not ok:
                bad.append((part, hex(d['Graphic']), d['Bone'], (d['X'], d['Y'], d['Z']), (d['XRot'], d['YRot'],
                                                                                            d['ZRot'])))
    check('effects: placed and turned alike facing left and right (bone 0: height / ahead, Y 0 / 180 only; other '
          'bones: no offset, no turn)', bad, [])
    # v7: the skill's particle emitters themselves (v6's screenshots: Csg_Circle's lines shot up with him facing left,
    # down facing right): every one at the effect's origin, unturned, any spread / speed a full sphere
    import ptcl
    path = os.path.join(body_dir, '..', '..', '..', 'effect', 'supamario', 'supamario.010d0000.ptcl')
    if os.path.exists(path):
        p = ptcl.Ptcl(open(path, 'rb').read())
        bad = []
        for si in range(len(p.sets)):
            if not p.set_name(si).startswith('PtcSupamarioGfCsg'):
                continue
            for e in p.sets[si]['emitters']:
                d = e['data']
                if d is None:
                    continue
                moving = (p.field(d, 'particle_type') in (1, 3) or p.field(d, 'emitter_velocity')
                          or p.field(d, 'figure_velocity'))
                if any(p.field(d, 'emitter_rotation')) or any(p.field(d, 'emitter_translation')) or \
                        (moving and p.field(d, 'dispersion_angle') < 180):
                    bad.append((p.set_name(si), p.emitter_name(d)))
        check('the skill\'s emitters: unturned, at the origin, spreading every way (alike with either facing)',
              bad, [])


def diag_tests(game_bin):
    """the diag build: its log lines (k, value) in a full God Fist"""
    f = acmd.ACMDFile.load(game_bin)
    script = f.script('attackdash')
    v = Victim()
    a, rec = run_move(script, v)
    ks = [k for k, _v in a.diag]
    got = dict((k, val) for k, val in reversed(a.diag))          # the first of each
    check('diag: catch kinds 2 (a hurtbox), slot %d, hold frames %d / %d, strike kinds 2, flight from slot %d'
          % (v.slot, B.JUMP_TO, B.STRIKE - 1, v.slot),
          ([val for k, val in a.diag if k == B.D_CATCH_KINDS], got.get(B.D_SLOT),
           [val for k, val in a.diag if k == B.D_HOLD_FRAME], [val for k, val in a.diag if k == B.D_STRIKE_KINDS][-1],
           [val for k, val in a.diag if k == B.D_FLIGHT][0]),
          ([2.0], float(v.slot), [float(B.JUMP_TO), float(B.STRIKE - 1)], 2.0, float(v.slot)))
    check('diag: target 2\'s rotation read in the flight (spun at flight frames 1 / 22 / 44) and its slot',
          ([val != 0.0 for k, val in a.diag if k == B.D_HOLD_ROT][-3:],
           [val for k, val in a.diag if k == B.D_SLOT][-3:]), ([True, True, True], [float(v.slot)] * 3))
    check('diag: no hold release in a clean run', B.D_WD_RELEASE in ks, False)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
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
    vm = R.VM(os.path.join(d, 'script', 'msc', 'supamario.mscsb'))
    if '--no-msc-tick' not in sys.argv and len(vm.m.scripts) > 2321:      # v5's gf_tick (the last function)
        MscTick.PATH = os.path.join(d, 'script', 'msc', 'supamario.mscsb')
    game = os.path.join(d, 'script', 'animcmd', 'body', 'game.bin')
    facing_tests(os.path.join(d, 'script', 'animcmd', 'body'))
    acmd_tests(game)
    # the game's open rules every way round (Acmd: DEFER / BLOCK / T2_THREAD)
    if '--all-models' in sys.argv:
        for defer in (True, False):
            for block in (False, True):
                for th in (False, True):
                    if (defer, block, th) == (True, False, False):
                        continue
                    Acmd.DEFER, Acmd.BLOCK, Acmd.THREADS = defer, block, th
                    PREFIX[0] = '[defer %d, part block %d, threads %d] ' % (defer, block, th)
                    acmd_tests(game)
        Acmd.DEFER, Acmd.BLOCK, Acmd.THREADS = True, False, False
        PREFIX[0] = ''
    if any(acmd.new_var_name(c) == 'gf_wd' for c in acmd.ACMDFile.load(game).script('attackdash')) and any(
            c.name == 'SUB_FLOAT_2' and len(c.params) > 0 and B.DIAG_BASE <= c.params[0] < B.DIAG_BASE + 16
            for c in acmd.ACMDFile.load(game).script('attackdash')):
        diag_tests(game)
    print('%d problem(s)' % len(PROBLEMS))
    sys.exit(1 if PROBLEMS else 0)


if __name__ == '__main__':
    main()
