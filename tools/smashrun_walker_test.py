#!/usr/bin/env python3
"""Unicorn test of tools/smashrun_walker_cave.py in a patched cross_f.rpx:

  python3 tools/smashrun_walker_test.py [--keep-flip] PATCHED.rpx [ENEMY_ROOT]

ENEMY_ROOT (optional): the installed converted enemies (motion/enemy/<name>/body/main.pac, animcmd/enemy/<name>/):
then every set entry must be an OMO of K's pac and every script of K's animcmd files a hash of K's script hashsets.

Runs the cave's code and the game's around it, the framework's calls stubbed (modules are fake objects):
- the hook words; the three spaces holding only the cave's code and data (zeros after);
- the factory 0x02DB94CC: each walker kind -> operator new(OBJ_SIZE), the Behavior ctor (obj, acc, K, variation),
  module+8 = obj with vptr VT, BehaviorImpl's init, +0x168 its CFG, its hashsets and nine damage labels; 2a's kinds
  and the twins / bosses still call their own create, other kinds none;
- the vtable (BehaviorImpl's but the overrides), slots 64-67 the kind's 3DS states, slot 38 0;
- fix v3 (the twins' slot 38, initialize_after's set_lr, notify_on_remove's type);
- change_state per kind: its 3DS state table (unknown / empty ids -> 1);
- initialize (the kind's energy words, the kick), start (face the target, the first state: Waddle Dee 2 for
  variations 0 / 1), set_attack_data (the kind's attacks only in their states: the contact attack in the Kuribo's
  5 and the Shy Guy's 9, the bullet attack in each death state, nothing else);
- each kind's behaviour in a small world (ground / walls / ledges / the target's search / the speed's y / the
  motion's end stubbed, x moved by the AI stick): the 3DS state sequences of README (Fix v5);
- T2 / S2, the sets and hashsets.
Step 2n: the machine guards every test file's runs: a guest write past the object's own SIZE (CFG SIZE, what operator
new got) and a run that hits its instruction cap without returning are failures (overrun_check(), called by each
test file at its end): a heap overrun or a freeze in game.
"""
import os
import struct
import sys
import zlib

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.ppc_const import UC_PPC_REG_LR, UC_PPC_REG_PC, UC_PPC_REG_MSR

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_field_cave as F  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402

pc = __import__('unicorn.ppc_const', fromlist=['x'])
R = {n: getattr(pc, 'UC_PPC_REG_%d' % n) for n in range(32)}
FR = {n: getattr(pc, 'UC_PPC_REG_FPR%d' % n) for n in range(32)}
HEAP, STACK = 0x30000000, 0x31000000
OBJ, ACC, MOD = HEAP + 0x1000, HEAP + 0x10000, HEAP + 0x200
ATKM, GROUND, EKIN, MOTION, KIN, POSTURE = (HEAP + 0x20000 + 0x100 * i for i in range(6))
KVT, ARRP, ARR, EN, INPUT, PM, MGR, FLAGS = (HEAP + 0x21000 + 0x100 * i for i in range(8))
KICK = 0x02000004               # the kinetic vt+0xFC target (a stub address)
KICK2 = 0x02000008              # vt+0xEC (step 2c: the 3DS's vt+0x74 kick of the White Bear's jumps)
ATK_MSC = 0x0200000C            # the AttackModule's MSC entry vt+0x334 (step 2c v2: the bear's absolute hit)
AVT = HEAP + 0x22000
DONE = 0x02000000               # return address of a run
VIS_STUB, SOUND_SET = 0x02000060, 0x02000064   # step 2i: ModelModule vt+0x164 / SoundModule vt+0x84 stubs
CREATES = {0x50: 0x02DD0438, 0x51: 0x02DC7414, 0x52: 0x026B7344, 0x53: 0x026C2E9C, 0x54: 0x026BE944,
           0x55: 0x026BB3E8, 0x56: 0x026C5F80, 0x57: 0x026CF4DC, 0x58: 0x026CBA64, 0x59: 0x026D1DFC,
           0x5A: 0x026D6834, 0x5B: 0x02DDB82C, 0x5E: 0x026E24EC, 0x5F: 0x026D80A0, 0x60: 0x026DB864}
REVERSE_LR = 0x026A7A20
SET_LR = 0x026A780C
FAILS = []
RUNAWAYS = []                   # step 2n: (start, pc) runs that hit the instruction cap without returning
OVERRUNS = []                   # step 2n: (kind, offset, size, pc) writes past an object's SIZE
VT_ADDR = [0]
EXTRA_STUBS = {}                # step 2j: cave labels run as stubs (the aerial helpers), filled by main
GKINDS = [w for w in W.WALKERS if not w.get('flier') and not w.get('step2h')]   # the walkers (step 2e's fliers:
# smashrun_flier_test.py; step 2h's kinds: smashrun_step2h_test.py)
WM_SETF, WM_SETI = 0x02000010, 0x02000014   # step 2h: the fighter WorkModule's set_float / set_int (vt +0x4C / +0x8C)


def overrun_check():
    """step 2n: every write the cave made into an object stayed inside the object's SIZE (operator new's)"""
    stuck = sorted(set(RUNAWAYS))
    check(not stuck, 'every run returns within 50000 instructions (start, pc): %s'
          % ', '.join('(0x%08X, 0x%08X)' % o for o in stuck[:12]))
    seen = sorted(set(OVERRUNS))
    check(not seen, 'no write past an object\'s SIZE (kind, offset, size, pc): %s'
          % ', '.join('(0x%X, +0x%X, %d, 0x%08X)' % o for o in seen[:12]))


def check(cond, what):
    print(('ok    ' if cond else 'FAIL  ') + what)
    if not cond:
        FAILS.append(what)


def f2d(v):
    return struct.unpack('>d', struct.pack('>Q', v))[0]


class Machine:
    def __init__(self, img):
        uc = self.uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        uc.mem_map(0x02000000, 0x03000000)
        uc.mem_map(0x10000000, 0x00800000)
        for base, data in img.mem:
            if 0x02000000 <= base < 0x05000000 or 0x10000000 <= base < 0x10800000:
                uc.mem_write(base, data[:max(0, min(len(data), 0x05000000 - base))]
                             if base < 0x05000000 else data)
        uc.mem_map(HEAP, 0x40000)
        uc.mem_map(STACK - 0x10000, 0x20000)
        uc.mem_write(DONE, struct.pack('>IIII', 0x48000000, 0x48000000, 0x48000000, 0x48000000))  # stop addresses
        self.calls = []
        self.sounds = []                # step 2m: play_se / stop_se
        self.ground, self.walls, self.cliff, self.motion_end = True, set(), False, False
        self.target, self.target_x = 0, 0.0
        self.found, self.vy, self.stopped = -1, 0.0, True
        self.creates = dict((v, k) for k, v in CREATES.items())
        self.vt = VT_ADDR[0]
        uc.hook_add(UC_HOOK_CODE, self.hook)
        # step 2n: the object's own size (CFG SIZE, operator new's) guarded: a write past it is a heap overrun in game
        self.obj_size, self.overruns = None, []
        uc.hook_add(UC_HOOK_MEM_WRITE, self.guard, begin=OBJ, end=ACC - 1)
        self.meshes, self.objects = {}, {}     # step 2i: NUD mesh -> visible; battle object id -> object
        # fake modules
        w = self.w32
        w(ACC + 0x30C8, ATKM)
        w(ACC + 0x30DC, GROUND)
        w(ACC + 0x30E8, EKIN)
        w(ACC + 0x30F0, MOTION)
        w(ACC + 0x3130, KIN)
        w(ACC + 0x311C, POSTURE)
        w(KIN, KVT)
        w(KVT + 0xFC, KICK)
        w(KVT + 0xEC, KICK2)
        w(ATKM, AVT)
        w(AVT + 0x334, ATK_MSC)
        self.situation = {}             # fighter accessor -> MSC StatusModule(1) (0 ground)
        self.work = {}                  # step 2h: fighter WorkModule writes {(module, id): value}
        w(KIN + 8, ARRP)
        w(ARRP, ARR)
        w(ARR + 4, EN)
        w(ARR + 0x14, FLAGS)
        w(W.PARAM_MGR, HEAP + 0x25000)          # step 2j: the gl entries (every kind -> entry 0; gravity 0.25)
        w(HEAP + 0x25000 + W.GL_BASE, HEAP + 0x26000)
        self.wf(HEAP + 0x26000 + 0x120, 0.25)

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack('>I', v & 0xFFFFFFFF))

    def r32(self, a):
        return struct.unpack('>I', self.uc.mem_read(a, 4))[0]

    def wf(self, a, v):
        self.uc.mem_write(a, struct.pack('>f', v))

    def rf(self, a):
        return struct.unpack('>f', self.uc.mem_read(a, 4))[0]

    def guard(self, u, _access, addr, size, value, _):
        if self.obj_size is not None and addr + size > OBJ + self.obj_size:
            pcv = u.reg_read(UC_PPC_REG_PC)
            self.overruns.append((addr - OBJ, size, pcv))
            OVERRUNS.append((self.obj_kind, addr - OBJ, size, pcv))

    def ret(self, r3=None):
        if r3 is not None:
            self.uc.reg_write(R[3], r3 & 0xFFFFFFFF)
        self.uc.reg_write(UC_PPC_REG_PC, self.uc.reg_read(UC_PPC_REG_LR))

    def fr(self, n):
        return f2d(self.uc.reg_read(FR[n]))

    def hook(self, u, addr, size, _):
        r = lambda n: u.reg_read(R[n])  # noqa: E731
        c = self.calls
        if addr in EXTRA_STUBS or addr in (W.CHECK_CLIFF_DIST, W.CREATE_DEAD_ITEM, W.AER_CTOR, W.AER_UPDATE_XY,
                                           W.IN_VIEW):
            # step 2j: Goomba's notice ledge / collapse dead item, the aerial module (Waddle Dee), the bear's view
            c.append((EXTRA_STUBS.get(addr, hex(addr)),))
            self.ret(int(self.cliff) if addr == W.CHECK_CLIFF_DIST else (1 if addr == W.IN_VIEW else None))
            return
        if addr == W.PLAY_SE:               # step 2m: the sounds, kept apart from the call lists
            self.sounds.append(('play', r(3), r(4), r(5)))
            self.ret(0x5E00 + len(self.sounds))
            return
        if addr == W.STOP_SE:
            self.sounds.append(('stop', r(3), r(4), r(5)))
            self.ret()
            return
        if addr in self.creates:
            c.append(('create', addr, r(3), r(4), r(5)))
            self.ret(0x7000 + r(4))
        elif addr == W.OPNEW:
            c.append(('new', r(3)))
            self.uc.mem_write(OBJ, b'\xCC' * r(3))
            self.ret(OBJ)
        elif addr == W.BEH_CTOR:
            c.append(('ctor', r(3), r(4), r(5), r(6)))
            self.w32(r(3), r(4))
            self.w32(r(3) + 4, 0)
            self.w32(r(3) + 8, r(5))
            self.w32(r(3) + 0xC, r(6))
            self.w32(r(3) + 0xE0, 0x1234)
            self.ret(r(3))
        elif addr == W.CHANGE_KINETIC:
            c.append(('kinetic', r(3), r(4)))
            self.ret()
        elif addr == W.NODE_GPOS:            # step 2g v5: the tread box on a live node (posture + node_off)
            c.append(('node_gpos', r(3), r(4), r(6)))
            off = getattr(self, 'node_off', (0.0, 11.72))
            self.wf(r(5), self.rf(POSTURE + 0x10) + off[0])
            self.wf(r(5) + 4, self.rf(POSTURE + 0x14) + off[1])
            self.wf(r(5) + 8, 0.0)
            self.ret()
        elif addr == W.SET_ATTACH_GROUND:
            c.append(('attach', r(3), r(4)))
            self.ret()
        elif addr == W.SET_MOTION_LABEL:
            self.w32(r(3) + 0xA8, r(5))
            self.ret()
        elif addr == W.SET_DAMAGE_LABEL:
            for i, x in enumerate((r(4), r(5), r(6), r(7), r(8), r(9), r(10))):
                self.w32(r(3) + 0xB0 + 4 * i, x)
            sp = r(1)
            self.w32(r(3) + 0xCC, self.r32(sp + 8))
            self.w32(r(3) + 0xD0, self.r32(sp + 0xC))
            self.ret()
        elif addr == W.CHANGE_MOTION:
            c.append(('motion', r(3), r(4), round(self.fr(1), 4), round(self.fr(2), 4), r(5), round(self.fr(3), 4)))
            self.w32(MOTION + W.MOT_KIND, r(4))      # step 2i: the MotionModule's motion playing (+0x38)
            self.ret()
        elif addr == W.MSC_STATUS:
            ctx, args = r(3), r(4)
            words = [self.r32(self.r32(args) + 4 * i) for i in range(self.r32(args + 4))]
            c.append(('msc_status', self.r32(ctx + 4), tuple(words)))
            if words == [1]:
                self.ret(self.situation.get(self.r32(ctx + 4), 2))
            else:
                self.ret()
        elif addr == WM_SETF:
            c.append(('set_float', r(3), r(4), round(self.fr(1), 4)))
            self.work[(r(3), r(4))] = round(self.fr(1), 4)
            self.ret()
        elif addr == WM_SETI:
            c.append(('set_int', r(3), r(4), r(5)))
            self.work[(r(3), r(5))] = r(4)
            self.ret()
        elif addr == ATK_MSC:
            args = r(4)
            words = [self.r32(self.r32(args) + 4 * i) for i in range(self.r32(args + 4))]
            c.append(('atk_msc', r(3), tuple(words)))
            self.ret(1)
        elif addr == W.REQ_QUAKE:
            c.append(('quake', r(3), r(4)))
            self.ret()
        elif addr == W.REQ_EFFECT:
            c.append(('effect', r(3), r(4), tuple(round(self.rf(r(5) + 4 * i), 3) for i in range(3)),
                      tuple(round(self.rf(r(6) + 4 * i), 3) for i in range(3)), round(self.fr(1), 3)))
            self.ret(0x5555)
        elif addr == W.REQ_EFFECT0:
            c.append(('effect0', r(3), r(4), tuple(round(self.rf(r(5) + 4 * i), 3) for i in range(3)),
                      round(self.fr(1), 3)))
            self.ret(0x5556)
        elif addr == W.REQ_FOLLOW:
            c.append(('follow', r(3), r(4), r(5), tuple(round(self.rf(r(6) + 4 * i), 3) for i in range(3)),
                      tuple(round(self.rf(r(7) + 4 * i), 3) for i in range(3)), round(self.fr(1), 3)))
            self.ret(0x7777)
        elif addr == W.REMOVE_EFFECT:
            c.append(('remove_effect', r(3), r(4)))
            self.ret()
        elif addr == W.GEN_ART:                 # step 2l: Behavior::generate_article(id, bool) (the Dee's parasol)
            c.append(('gen_art', r(3), r(4), r(5)))
            self.ret()
        elif addr == W.BI_UPDATE:
            c.append(('bi_update', r(3), r(4)))
            self.ret()
        elif addr == W.NOTIFY_DEATH:
            c.append(('notify_death', r(3)))
            self.ret()
        elif addr == W.BULLET:
            c.append(('bullet', r(3)))
            self.ret()
        elif addr == W.IS_TOUCH:
            c.append(('touch', r(3), r(4)))
            self.ret(int(self.ground) if r(4) == 8 else int(r(4) in self.walls))
        elif addr == W.MOTION_IS_END:
            c.append(('is_end', r(3)))
            self.ret(int(self.motion_end))
        elif addr == W.NEAREST:
            c.append(('nearest', r(3)))
            self.ret(self.target)
        elif addr == W.CHECK_TURN:
            # check_turn_to_target (its prologue saves f31 with a paired-single store Unicorn can't run): the game's
            # test, 0x026A69C0-0x026A6A14: dx = target x - posture x; dx < -f1 and lr != -1, or dx > f1 and lr != 1
            c.append(('check_turn', r(4), self.fr(1)))
            if r(4) >= 0x80000000:
                self.ret(0)
            else:
                dx = self.target_x - self.rf(POSTURE + 0x10)
                lr = self.rf(POSTURE + 0x60)
                self.ret(int((dx < -self.fr(1) and lr != -1.0) or (dx > self.fr(1) and lr != 1.0)))
        elif addr == W.GET_TARGET_POS:
            c.append(('target_pos', r(5)))
            self.wf(r(3), self.target_x)
            self.wf(r(3) + 4, 0.0)
            self.wf(r(3) + 8, 0.0)
            self.ret()
        elif addr == W.SEARCH:
            c.append(('search', r(4), r(5), tuple(round(self.fr(i), 3) for i in range(1, 6))))
            self.ret(self.found)
        elif addr == W.GET_SPEED:
            self.wf(r(3), 0.0)
            self.wf(r(3) + 4, self.vy)
            self.wf(r(3) + 8, 0.0)
            self.ret()
        elif addr == W.CLEAR_SPEED:
            c.append(('clear_speed', r(3)))
            self.ret()
        elif addr == W.IS_STOPPED:
            self.ret(int(self.stopped))
        elif addr == W.CHECK_CLIFF_LR:
            c.append(('cliff', r(3), self.fr(1)))
            self.ret(int(self.cliff))
        elif addr == W.SET_RHOMBUS:
            c.append(('rhombus', r(3)))
            self.ret()
        elif addr == SET_LR:
            c.append(('set_lr', r(3), self.fr(1), r(4), r(5)))
            self.wf(POSTURE + 0x60, self.fr(1))
            self.ret()
        elif addr == W.SET_CORRECT:
            c.append(('set_correct', r(3), r(4)))
            self.ret()
        elif addr == 0x02C6108C:
            c.append(('flip', r(4)))
            self.ret()
        elif addr in (0x02C367C4, 0x02DB49F8, 0x02DB3518):
            self.ret()
        elif addr == 0x02DB3AB0:
            c.append(('defeat_fx', r(3)))
            self.ret()
        elif addr == 0x02DB3574:
            c.append(('vanish_fx', r(3)))
            self.ret()
        elif addr == REVERSE_LR:
            c.append(('reverse_lr', r(3), r(4), r(5)))
            lr = -self.rf(POSTURE + 0x60)
            self.wf(POSTURE + 0x60, lr)
            if r(5):
                self.wf(r(3) + 0x10, lr)
            self.ret()
        elif addr in (W.CHG_BASE, W.CHG_INT):
            pm = lambda p: (self.r32(p), self.r32(p + 4))  # noqa: E731
            c.append(('chg' if addr == W.CHG_BASE else 'chgi', r(3), r(4), pm(r(5)), pm(r(6)), pm(r(7))))
            self.w32(r(3) + 4, r(4))
            self.ret()
        elif addr == W.ATK_CLEAR:
            c.append(('atk_clear', r(3)))
            self.ret()
        elif addr == W.ATK_CREATE:
            c.append(('atk_create', r(3), r(4)))
            self.ret()
        elif addr == W.ATK_SET:
            c.append(('atk_set', r(3), r(4), r(5), r(6)))
            self.ret()
        elif addr == KICK2:
            c.append(('kick2', r(3), r(4)))
            self.ret()
        elif addr == KICK:
            c.append(('kick', r(3), r(4)))
            self.ret()
        elif addr == E.PARAM_LOAD:
            c.append(('load', r(3)))
            self.ret(0x1234)
        # step 2i: the mesh switch (h_vis: the model handle's is_valid / set_mesh_visibility_by_index; h_whole: the
        # ModelModule's vt+0x164, VIS_STUB in the fake ModelModules' vtables), Ghos's slot 31 lookups
        elif addr == W.MM_IS_VALID:
            self.ret(1)
        elif addr == W.MM_SET_MESH:
            c.append(('mesh', r(4), r(5)))
            self.meshes[r(4)] = r(5)
            self.ret(1)
        elif addr == VIS_STUB:
            c.append(('visible', r(4)))
            self.ret()
        elif addr == W.FIND_BO:
            c.append(('find_bo', r(3), r(5)))
            self.w32(r(4), self.objects.get(r(5), 0))
            self.w32(r(4) + 4, 0)
            self.ret()
        elif addr == W.BO_IS_NULL:
            self.ret(0 if self.r32(r(3)) else 1)
        elif addr == SOUND_SET:
            c.append(('sound_5ad', r(4)))
            self.ret()

    def stage(self, kind):
        self.w32(F.STAGE_KIND, kind)

    def run(self, start, stop, regs, fregs=None):
        for k, v in regs.items():
            self.uc.reg_write(R[k], v & 0xFFFFFFFF)
        for k, v in (fregs or {}).items():
            self.uc.reg_write(FR[k], struct.unpack('>Q', struct.pack('>d', v))[0])
        self.uc.reg_write(R[1], STACK)
        self.uc.reg_write(UC_PPC_REG_MSR, self.uc.reg_read(UC_PPC_REG_MSR) | 0x2000)
        self.uc.emu_start(start, stop, count=50000)
        if self.uc.reg_read(UC_PPC_REG_PC) != stop:      # step 2n: a run that never returns (a loop) is a freeze in game
            RUNAWAYS.append((start, self.uc.reg_read(UC_PPC_REG_PC)))

    def call(self, fn, regs, fregs=None):
        self.uc.reg_write(UC_PPC_REG_LR, DONE)
        self.run(fn, DONE, regs, fregs)

    def walker(self, cfg, state=0, lr=-1.0, x=0.0, kind=0, var=0):
        """a walker object (as create leaves it) with the fake modules"""
        self.obj_size = None
        self.uc.mem_write(OBJ, bytes(W.FL_SIZE))
        self.w32(OBJ, ACC)
        self.w32(OBJ + 4, state)
        self.w32(OBJ + 8, kind)
        self.w32(OBJ + 0xC, var)
        self.w32(OBJ + 0x168, cfg)
        self.w32(OBJ + 0xE0, self.vt)
        self.obj_size, self.obj_kind = self.r32(cfg + W.CF['SIZE']), kind
        self.wf(OBJ + 0x10, lr)
        self.wf(POSTURE + 0x10, x)
        self.wf(POSTURE + 0x14, 0.0)
        self.wf(POSTURE + 0x60, lr)


class World:
    """frames of one walker: the deferred change_state takes effect next frame (enter, then update), the interrupt
    one at once (its enter now); a one-shot motion ends 5 frames after it starts; x += 2 * the AI stick"""

    def __init__(self, m, w, rows, state, cfg):
        self.m, self.w, self.rows, self.cfg = m, w, rows, cfg
        self.cur, self.pending, self.mframes, self.oneshot = state, None, 0, False
        self.log, self.script, self.i = [], {}, 0
        self.enter(state)

    def enter(self, s):
        m = self.m
        m.calls = []
        self.cur = s
        if self.rows[s][0] == W.ZIMA_REMOVE_ENTER:          # the game's remove state: not run here
            return []
        m.call(self.rows[s][0], {3: OBJ})
        self.track(m.calls)
        return m.calls

    def track(self, calls):
        for c in calls:
            if c[0] == 'motion':
                self.mframes, self.oneshot = 0, not c[5]

    def frame(self):
        m = self.m
        if self.i in self.script:
            self.script[self.i](self)
        en = []
        if self.pending is not None:
            en = self.enter(self.pending)
            self.pending = None
        m.motion_end = self.oneshot and self.mframes >= 5
        self.mframes += 1
        m.calls = []
        m.uc.mem_write(INPUT, struct.pack('>ff', 7.0, 7.0))
        m.call(self.rows[self.cur][1], {3: OBJ, 4: INPUT})
        calls = list(m.calls)
        self.track(calls)
        stick = struct.unpack('>ff', m.uc.mem_read(INPUT, 8))
        x = m.rf(POSTURE + 0x10) + (2.0 * stick[0] if stick[0] != 7.0 else 0.0)
        m.wf(POSTURE + 0x10, x)
        for c in calls:
            if c[0] == 'chg':
                self.pending = c[2]
        ints = [c for c in calls if c[0] == 'chgi']
        st = self.cur
        if ints:
            self.pending = None
            en = self.enter(ints[-1][2])
        self.log.append((self.i, st, round(x, 1), stick, calls, en))
        self.i += 1

    def run(self, n):
        for _ in range(n):
            self.frame()

    def states(self, since=0):
        out = []
        for e in self.log[since:]:
            if not out or out[-1] != e[1]:
                out.append(e[1])
        return out


def main():
    if '--keep-flip' in sys.argv:            # the variant built with smashrun_walker_cave.py --keep-flip
        sys.argv.remove('--keep-flip')
        W.KEEP_FLIP = True
    img = E.Image(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else None
    vt_words = W.read_vt(img)
    A, B, d = W.assemble(vt_words)
    D = d.addr
    VT_ADDR[0] = D['vt']
    cfg = {w['kind']: D['cfg_' + w['name']] for w in W.WALKERS}
    fn = dict(A.labels)
    EXTRA_STUBS.update({fn[k]: k for k in ("f_amode", "f_aupd", "f_anone")})     # step 2j: the aerial helpers
    byname = {w['name']: w for w in W.WALKERS}

    # hooks and space
    check(all(img.u32(s) == W.branch(s, fn[f]) for s, f in ((W.SITE_F, 'cave_f'), (W.SITE_T, 'cave_t'),
                                                            (W.SITE_S, 'cave_s'), (W.SITE_ROT, 'cave_rot'),
                                                            (W.SITE_DEATH, 'cave_death'))),
          'hooks: F2 / T2 / S2 / initialize_after / notify_on_remove branch to the cave')
    want = {}
    for a in (A, B, A.area, A.stomp, A.e, A.g, A.h):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    for base, words in d.chunks:
        want.update({base + 4 * i: x for i, x in enumerate(words)})
    bad = [hex(x) for lo, hi in W.REGIONS for x in range(lo, hi, 4) if img.u32(x) != want.get(x, 0)]
    check(not bad, 'space %s: the code (A to 0x%08X, B to 0x%08X, C to 0x%08X, E to 0x%08X), the data, zeros '
          'after %s' % (', '.join('0x%08X-0x%08X' % r for r in W.REGIONS), A.pc, B.pc, A.area.pc, A.e.pc, bad[:4]))
    check(all(img.u32(s_) == W.branch(s_, fn['area_%d' % i]) for i, (s_, _w, _d, _b, _k, _x) in
              enumerate(W.AREA_SITES)), 'fix v7: the three area-table sites (0x02D89898 0x02D8A24C 0x02D8FB98) '
          'branch to the cave')
    cave_f_2a = E.assemble(E.build_sets(img))[0].addr('cave_f')
    check(img.u32(E.SITE_F) == W.branch(E.SITE_F, cave_f_2a),
          'step 2a\'s factory hook still in place (0x%08X)' % E.SITE_F)

    # the factory
    for w in GKINDS:
        k = w['kind']
        m = Machine(img)
        m.w32(MOD + 4, ACC)
        m.w32(MOD + 8, 0)
        m.run(0x02DB94CC, 0x02DB96F8, {3: MOD, 4: k, 5: 0, 6: 2})
        o = OBJ
        init = [m.r32(o + x) for x in range(0xE4, W.OBJ_SIZE, 4)]
        exp = []
        for x in range(0xE4, W.OBJ_SIZE, 4):
            v = 0
            if x == 0xE8:
                v = img.u32(W.COMMON_PMF)
            elif x == 0xEC:
                v = img.u32(W.COMMON_PMF + 4)
            elif x == 0x120:
                v = 0x01000000
            elif x == 0x15C:
                v = 0xFFFFFFFF
            elif x == 0x168:
                v = cfg[k]
            exp.append(v)
        calls = [c for c in m.calls if c[0] in ('new', 'ctor', 'create')]
        labels = [m.r32(o + 0xB0 + 4 * i) for i in range(9)]
        want_labels = [0xCCCCCCCC] * 9 if w.get('no_damage_labels') else W.damage_labels(w)    # none: not called
        check(calls == [('new', w.get('size', W.OBJ_SIZE)), ('ctor', OBJ, ACC, k, 2)] and m.r32(MOD + 8) == OBJ and
              m.r32(o + 0xE0) == D['vt_' + w['name'] if w.get('vtover') else 'vt'] and init == exp and m.r32(o + 0xA8) == D.get('hs_' + w['name'], 0) and
              labels == want_labels and m.r32(o + 8) == k,
              'F2: %s 0x%02X -> new(0x%X), ctor(acc, K, var), module+8, vptr VT, BehaviorImpl init, CFG, '
              'hashsets 0x%X, damage labels %s' % (w['name'], k, w.get('size', W.OBJ_SIZE), m.r32(o + 0xA8), labels))
    res = {}
    for k in [0x30, 0x0E, 0x12, 0x1D, 0x57, 0x5A, 0x50, 0x60, 0x00, 0x02, 0x2F, 0x4F, 0x61]:
        m = Machine(img)
        m.w32(MOD + 4, ACC)
        m.w32(MOD + 8, 0)
        m.run(0x02DB94CC, 0x02DB96F8, {3: MOD, 4: k, 5: 0, 6: 0})
        res[k] = ([c[1:] for c in m.calls if c[0] in ('create', 'new')], m.r32(MOD + 8))
    twins = {p[1]: p[3] for p in E.PAIRS}
    ok = all(res[k] == ([(twins[k], ACC, k, 0)], 0x7000 + k) for k in twins)
    ok &= all(res[k] == ([(CREATES[k], ACC, k, 0)], 0x7000 + k) for k in (0x57, 0x5A, 0x50, 0x60))
    ok &= all(res[k] == ([], 0) for k in (0x00, 0x02, 0x2F, 0x4F, 0x61))
    check(ok, 'F2: 2a\'s kinds call their twins\' create, 0x50-0x60 their own, 0x00 0x02 0x2F 0x4F 0x61 none')

    # the vtable
    vt = [img.u32(D['vt'] + 4 * i) for i in range((0xC + 8 * 76) // 4)]
    slots = {k: vt[(0xC + 8 * k) // 4] for k in range(76)}
    bi = {k: vt_words[(0xC + 8 * k) // 4] for k in range(74)}
    over = {12: W.ZIMA_CAPTURE_MOTION, 38: W.ZIMA_ONE if W.KEEP_FLIP else fn['w_noflip'], 40: fn['w_init'],
            3: fn['w_upd'], 41: fn['w_start'], 45: fn['w_atk'], 20: fn['w_tread'], 64: fn['w_r64'], 65: fn['w_r65'], 66: fn['w_r66'],
            67: fn['w_r67'], 72: fn['w_chg'], 73: fn['w_chgi'], 74: fn['w_chg'], 75: fn['w_chgi'],
            49: fn['w_slr'], 50: fn['w_rlr']}
    ok = vt[:3] == vt_words[:3] and all(slots[k] == over.get(k, bi.get(k)) for k in range(76))
    ok &= all(vt[(0x8 + 8 * k) // 4] == 0 for k in range(76))
    ok &= bi[49] == W.SET_LR and bi[50] == W.REVERSE_LR
    check(ok, 'VT: BehaviorImpl\'s 74 slots (dtor 0x%08X, update 0x%08X kept) with 12 38 40 41 45 49 50 64-67 72-75 '
          'overridden (49 / 50 were set_lr 0x%08X / reverse_lr 0x%08X)' % (slots[0], slots[3], bi[49], bi[50]))
    # step 2g v3: the twins' vtables (2a's zima / plasmawisp / darios) slots 49 / 50 -> the same wrappers
    got = [(hex(w), img.u32(w) == fn[lab]) for w, _o, lab in W.TWIN_LR]
    check(all(g for _w, g in got), 'step 2g v3: the twins\' vtable slots 49 / 50 -> w_slr / w_rlr %s' % got)
    # step 2g v3, w_yaw (after set_lr / reverse_lr): the 3DS-flip kinds keep yaw -90 at lr 1 (their lr -1 view, which
    # the 3DS mirrors), every other kind lr x 90; the model / motion marks as set_lr's
    YK = HEAP + 0x3F000
    res = {}
    for k in sorted(set(W.YAW_FLIP) | {0x0B, 0x30, 0x40, 0x08, 0x11, 0x5A, 0x57}):
        for lr in (1.0, -1.0):
            m = Machine(img)
            m.w32(YK, ACC)
            m.w32(YK + 8, k)
            m.uc.mem_write(ACC + 0x3118, struct.pack('>I', HEAP + 0x3F400))
            m.uc.mem_write(HEAP + 0x3F400, bytes(0x40))
            m.w32(HEAP + 0x3F420, 7)
            m.w32(ACC + 0x30F0, HEAP + 0x3F800)
            m.w32(HEAP + 0x3F800 + 0xFC, 1)
            m.wf(POSTURE + 0x60, lr)
            m.wf(POSTURE + 0x64, lr * 90.0)
            m.call(fn['w_yaw'], {3: YK})
            res[(k, lr)] = (m.rf(POSTURE + 0x64), m.r32(HEAP + 0x3F420), m.r32(HEAP + 0x3F800 + 0xFC))
    ok = all(v == ((-90.0, 0, 2) if (k in W.YAW_HOLD and lr == 1.0) else (lr * 90.0, 7, 1)) for (k, lr), v in res.items())
    check(ok, 'step 2g v3 / v6: w_yaw: lr 1 -> yaw -90 (model +0x20 = 0, motion +0xFC 1 -> 2) only for the flip kinds '
          'without a model.flp %s; lr x 90 for lr -1, the flip kinds with one (now mirrored for real) and the others '
          '(Shy Guy, Stalfos, White Bear, Gordo, Ghos, the twins) %s'
          % ([hex(k) for k in W.YAW_HOLD], {('0x%X' % k, lr): v[0] for (k, lr), v in res.items() if lr == 1.0}))
    # step 2g v6: slot 38 (is_flip_model) of the walker vtables: 1 for the FLIP_TABLE kinds (set_lr / reverse_lr then
    # flip the motion: MotionModule 0x02C6108C(lr == 1, 1)), 0 for every other kind
    got = {}
    for k in sorted(set(W.YAW_FLIP) | {0x0B, 0x30, 0x40, 0x08, 0x11, 0x5A, 0x57, 0x23, 0x5F}):
        m = Machine(img)
        m.w32(OBJ + 8, k)
        m.call(fn['w_noflip'], {3: OBJ})
        got[k] = m.uc.reg_read(R[3])
    check(all(v == (1 if k in W.FLIP_TABLE else 0) for k, v in got.items()),
          'step 2g v6: slot 38 w_noflip -> 1 for the kinds with a model.flp %s, 0 for the rest %s'
          % ([hex(k) for k in W.FLIP_TABLE], {hex(k): v for k, v in got.items()}))
    for w in GKINDS:
        m = Machine(img)
        m.walker(cfg[w['kind']], state=3, kind=w['kind'])
        m.call(slots[20], {3: OBJ, 4: 0x11, 5: 0})
        c = [x for x in m.calls if x[0] in ('chg', 'chgi')]
        t = w.get('tread', 0)
        check(c == ([('chgi', OBJ, t, (0xFFFF, fn[w['states'][t][1]]), (0xFFFF, fn[w['states'][t][0]]), (0, 0))]
                    if t else []) and len(m.calls) == len(c),
              'VT %s: slot 20 (the 3DS\'s 21, stepped on) %s' % (w['name'], '=> %d (collapses)' % t if t else
                                                                  'does nothing (BehaviorImpl\'s nop, as on the 3DS)'))
    for w in GKINDS:
        got = []
        for k in (64, 65, 66, 67):
            m = Machine(img)
            m.walker(cfg[w['kind']])
            m.call(slots[k], {3: OBJ})
            got.append(m.uc.reg_read(R[3]))
        check(tuple(got) == w['rets'], 'VT %s: slots 64-67 (after damage on the ground / in the air / default, '
              'death) = the 3DS\'s %s' % (w['name'], got))
    m = Machine(img)
    m.call(slots[38], {3: OBJ})
    flip = 1 if W.KEEP_FLIP else 0
    check(m.uc.reg_read(R[3]) == flip, 'VT: slot 38 (flip the motion with lr) %d' % flip)

    # fix v3: the twins' slot 38, initialize_after's set_lr, notify_on_remove's type
    res = {}
    for word, orig in W.TWIN_FLIP:
        f = img.u32(word)
        for k in (0x12, 0x0E, 0x1D, 0x30, 0x57, 0x5A, 0x58):
            m = Machine(img)
            m.w32(OBJ + 8, k)
            m.call(f, {3: OBJ})
            res[(word, k)] = m.uc.reg_read(R[3])
        res[word] = f
    if W.KEEP_FLIP:
        ok = all(res[w] == o for w, o in W.TWIN_FLIP)
    else:
        ok = all(res[w] == fn['twin_flip'] for w, _o in W.TWIN_FLIP)
        ok &= all(res[(w, k)] == (1 if k >= 0x50 or k in W.FLIP_TABLE else 0) for w, _o in W.TWIN_FLIP
                  for k in (0x12, 0x0E, 0x1D, 0x30, 0x57, 0x5A, 0x58))
    check(ok, 'fix v3 / step 2g v6: the twins\' slot 38 (zima / plasmawisp / darios vtables) %s'
          % ('kept (variant)' if W.KEEP_FLIP else '-> 1 for the Fortress minions and the Smash Run twins with a '
             'model.flp (zima, plasmawisp, darios), 0 for Stalfos'))
    got = {}
    for k in (0x01, 0x12, 0x57, 0x60):
        m = Machine(img)
        m.walker(cfg[1], lr=-1.0, kind=k)
        m.calls = []
        m.call(0x02DB4AC8, {3: OBJ})
        got[k] = [c for c in m.calls if c[0] in ('set_lr', 'flip')]
    ok = all(got[k][-1:] == [('set_lr', OBJ, -1.0, 1, 1)] for k in (0x01, 0x12)) and \
        all(not [c for c in got[k] if c[0] == 'set_lr'] for k in (0x57, 0x60))
    check(ok, 'fix v3: initialize_after calls set_lr(posture lr, 1, 1) for kinds < 0x50 only %s' % got)
    got = {}
    for k, t, dead, ours in ((0x01, 0, 1, 1), (0x01, 0, 0, 1), (0x12, 0, 0, 0), (0x01, 5, 1, 1), (0x01, 1, 1, 1),
                             (0x57, 0, 0, 0), (0x01, 3, 0, 1)):
        m = Machine(img)
        m.walker(cfg[1], kind=k)
        m.w32(OBJ + W.DEFEATED, dead)
        if not ours:
            m.w32(OBJ + 0xE0, 0x1234)           # a twin's own vtable
        m.calls = []
        m.call(W.SITE_DEATH, {3: OBJ, 4: t})
        got[(k, t, dead)] = [c[0] for c in m.calls if c[0] in ('defeat_fx', 'vanish_fx')]
    # (a type-0 removal goes to 0x02DB3574, the minions' vanish path, which does nothing for kinds below 0x57)
    check(got == {(0x01, 0, 1): ['defeat_fx'], (0x01, 0, 0): ['vanish_fx'], (0x12, 0, 0): ['defeat_fx'],
                  (0x01, 5, 1): [],
                  (0x01, 1, 1): [], (0x57, 0, 0): ['vanish_fx'], (0x01, 3, 0): ['defeat_fx']},
          'fix v3 / step 2c v2: notify_on_remove: a walker kind removed after its death / collapse (DEFEATED set) or a '
          'twin kind < 0x50 removed by its behaviour (type 0) takes the defeat effect path; a walker that leaves '
          '(DEFEATED 0) is removed silently; '
          '0x02DB3AB0 (type 3); the minions keep type 0; other types unchanged %s' % got)

    # change_state: the kind's table
    rows = {}
    for w in GKINDS:
        r = {}
        for sid, s in w['states'].items():
            if s == 'remove':
                s = (W.ZIMA_REMOVE_ENTER, W.ZIMA_REMOVE_UPDATE)
            r[sid] = tuple(x if isinstance(x, int) else fn[x] for x in s)
        rows[w['name']] = r
        for slot, kind in ((72, 'chg'), (73, 'chgi')):
            ok = True
            for sid in list(range(0, W.nstates(w) + 2)) + [99, -1]:
                m = Machine(img)
                m.walker(cfg[w['kind']])
                m.call(slots[slot], {3: OBJ, 4: sid})
                c = [x for x in m.calls if x[0] in ('chg', 'chgi')]
                eid = sid if sid in r else 1
                en, up = r[eid][:2]
                ex = (0xFFFF, r[eid][2]) if len(r[eid]) > 2 else (0, 0)    # step 2f / 2m: a state's exit
                ok &= c == [(kind, OBJ, eid, (0xFFFF, up), (0xFFFF, en), ex)]
            check(ok, 'change_state %s slot %d -> 0x%08X(this, id, &update, &enter, &exit): states %s, others -> 1'
                  % (w['name'], slot, W.CHG_BASE if slot == 72 else W.CHG_INT, sorted(r)))

    # initialize / start / set_attack_data
    for w in GKINDS:
        k, c0 = w['kind'], cfg[w['kind']]
        m = Machine(img)
        m.walker(c0)
        m.call(fn['w_init'], {3: OBJ})
        got = {o: round(m.rf(EN + o), 6) for o in range(0, 0x80, 4) if m.r32(EN + o)}
        exp = {o: round(v, 6) for o, v in w['energy'].items() if v}
        kicks = [x for x in m.calls if x[0] == 'kick']
        check(got == exp and kicks == ([('kick', KIN, 0x20000004)] if w['kick'] else []),
              'initialize %s: kinetic energy %s%s' % (w['name'], {hex(o): v for o, v in got.items()},
                                                      ', vt+0xFC(0x20000004)' if w['kick'] else ''))
        for var in (0, 2):
            m = Machine(img)
            m.walker(c0, lr=-1.0, x=0.0, var=var)
            m.target, m.target_x = 0, 50.0
            m.wf(OBJ + 0x14, 9.0)
            m.w32(W.V(3) + OBJ, 5)
            m.call(fn['w_start'], {3: OBJ})
            seq = [x[0] for x in m.calls]
            chg = [x for x in m.calls if x[0] == 'chg']
            first = w['start'][1] if var <= 1 else w['start'][0]
            if w.get('smode'):
                check(seq[:1] == ['rhombus'] and 'reverse_lr' not in seq and 'nearest' not in seq and chg and
                      chg[-1][2] == first and [c for c in m.calls if c[0] in ('set_correct', 'set_lr')] ==
                      [('set_correct', GROUND, 0), ('set_lr', OBJ, 0.0, 1, 1)] and m.rf(OBJ + 0x10) == 0.0 and
                      m.rf(OBJ + 0x14) == 0.0 and m.r32(OBJ + W.V(3)) == 0,
                      'start %s (variation %d, the 3DS 0x19CB0): set_rhombus, set_correct(0), set_lr(0.0, 1, 1) (faces '
                      'the camera), +0x10 = 0, no turn to the target, change_state(%d)' % (w['name'], var, first))
                continue
            check(seq[:1] == ['rhombus'] and 'reverse_lr' in seq and chg and chg[-1][2] == first and
                  m.rf(OBJ + 0x10) == 1.0 and m.rf(OBJ + 0x14) == 0.0 and m.r32(OBJ + W.V(3)) == 0,
                  'start %s (variation %d): set_rhombus, +0x10 = lr, turns to the target behind, change_state(%d)'
                  % (w['name'], var, first))
        atks = {}
        for st, a in w['attacks']:
            atks.setdefault(st, []).append(D[a])
        ok = True
        for sid in range(0, W.nstates(w) + 1):
            m = Machine(img)
            m.walker(c0)
            m.call(fn['w_atk'], {3: OBJ, 4: sid})
            exp = [('atk_clear', ATKM)]
            for e in atks.get(sid, []):
                ent = [img.u32(e + 4 * i) for i in range(42)]
                exp += [('atk_create', OBJ, e), ('atk_set', ATKM, ent[1], ent[2], OBJ + 0x1C)]
            ok &= m.calls == exp
        for st, a in w['attacks']:
            ok &= [img.u32(D[a] + 4 * i) for i in range(42)] == [W.word(v) for v in W.ATTACKS[a]]
        check(ok, 'set_attack_data %s: clear_all; the 3DS vl attacks only in their states %s'
              % (w['name'], {st: a for st, a in w['attacks']}))

    def air(wo, n=3):
        wo.m.vy, wo.m.ground = 1.0, False
        wo.script[wo.i + n] = lambda w2: (setattr(w2.m, 'vy', -1.0), setattr(w2.m, 'ground', True))

    def world(name, state, lr=-1.0, var=0, setup=None):
        w = byname[name]
        m = Machine(img)
        m.walker(cfg[w['kind']], state=state, lr=lr, kind=w['kind'], var=var)
        m.w32(OBJ + W.V(7), w.get('leave', 0))       # as start leaves it (Waddle Doo's leave timer)
        if name == 'waddledoo':                       # step 2k: the beam's cool-down held (smashrun_step2k_test.py)
            m.w32(OBJ + W.DO_CD, 0x7FFFFFFF)
        m.target, m.target_x = 0, 300.0
        if setup:
            setup(m)
        return World(m, w, rows[name], state, cfg[w['kind']])

    def enters(name):
        """each state's enter: (kinetic, attach, (motion index, rate, loop)) as the 3DS's"""
        out = {}
        for sid, (en, _up, *_ex) in rows[name].items():
            if en == W.ZIMA_REMOVE_ENTER:
                continue
            m = Machine(img)
            m.walker(cfg[byname[name]['kind']], kind=byname[name]['kind'])
            m.call(en, {3: OBJ})
            k = [c[2] for c in m.calls if c[0] == 'kinetic']
            a = [c[2] for c in m.calls if c[0] == 'attach']
            mo = [(c[2], c[4], c[5]) for c in m.calls if c[0] == 'motion']
            out[sid] = (k[0] if k else None, a[0] if a else None, mo[0] if mo else None,
                        'bullet' if [c for c in m.calls if c[0] == 'bullet'] else '')
        return out

    # ---- fix v7: the area tables (area 0 = the tread area) per kind, the slot's for the other kinds
    ZT = HEAP + 0x30000
    for i, (site, _w, dst, base, kreg, shifted) in enumerate(W.AREA_SITES):
        got = {}
        for k in (0x01, 0x0B, 0x13, 0x19, 0x1F, 0x12, 0x5A, 0x30):
            m = Machine(img)
            m.uc.reg_write(R[dst], 0)
            m.run(fn['area_%d' % i], site + 4, {base: ZT - 0x70 + 0x70 * 0 + 0, kreg: k * 4 if shifted else k,
                                                  31: OBJ})
            got[k] = m.uc.reg_read(R[dst])
        m.w32(ZT, 0)
        exp = {k: (D['ar_' + byname_k['name']] if byname_k else 0) for k, byname_k in
               ((k, next((w for w in W.WALKERS if w['kind'] == k), None)) for k in got)}
        exp = {k: (v if v else m.r32(ZT)) for k, v in exp.items()}
        check(got == exp, 'fix v7: area site 0x%08X: a walker kind gets its own table, others the slot\'s +0x70 %s'
              % (site, {hex(k): hex(v) for k, v in got.items()}))
    for w in GKINDS:
        t = [img.u32(D['ar_' + w['name']] + 4 * j) for j in range(12)]
        check(t == [W.word(v) for e in w['areas'] for v in e], 'fix v7: %s area table %s (tread area %s)'
              % (w['name'], w['areas'], 'on' if w['areas'][0][0] else 'off, as on the 3DS'))
    # the game's area set-up 0x02D89860 for a Goomba: the tread area from its table (zima's slot: tread off)
    EN_OBJ = HEAP + 0x8000
    for k, want in ((0x01, (0xE, 2, 14.0, 8.0)), (0x5A, (0xE, 0, 12.0, 12.0))):
        m = Machine(img)
        m.uc.mem_write(EN_OBJ, bytes(0x3500))
        m.w32(EN_OBJ + 4, k)
        m.w32(EN_OBJ + 0x30F0, HEAP + 0x200)
        m.w32(W.PARAM_MGR, PM)
        m.w32(PM + 0x60 + 4 * k, HEAP + 0x30100)
        m.w32(HEAP + 0x30100 + 0x70, HEAP + 0x30200)
        for j, v in enumerate((0, 0, 12.0, 12.0, 0.0, 0.0, 1, 3, 8.0, 8.0, 0.0, 0.0)):
            m.uc.mem_write(HEAP + 0x30200 + 4 * j, struct.pack('>f', v) if isinstance(v, float) else
                           struct.pack('>I', v))
        sets = []

        def add_area(uc, addr, size, _u, mm=m, out=sets):
            if addr == 0x02BFEA2C:
                out.append(mm.r32(mm.uc.reg_read(R[4])))
                mm.ret()
        m.uc.hook_add(UC_HOOK_CODE, add_area, begin=0x02BFEA2C, end=0x02BFEA2C)
        m.call(0x02D89860, {3: EN_OBJ})
        e0 = EN_OBJ + 0x348C
        got = (m.uc.mem_read(e0 + 1, 1)[0], m.r32(e0 + 0xC), round(m.rf(e0 + 0x18), 3), round(m.rf(e0 + 0x1C), 3))
        check(sets == [e0] and got == want, 'fix v7: the game\'s area set-up (0x02D89860) for kind 0x%02X: '
              'area 0 (kind, node, size) %s' % (k, got))

    # ---- fix v8: the stomp detected in the walker's update (slot 3)
    FT, TBL, ENTS, FACC, FPOST, FSTAT, FWM, FWMVT = (HEAP + 0x34000 + 0x100 * i for i in range(8))

    def stomp(name, frames, state=3, ex=0.0, ey=0.0, count=1, live=4, node_off=None, calls_out=None):
        """frames: the fighter's (x, y) per frame; -> per frame (chgi states, msc status calls, bi_update calls)"""
        w = byname[name]
        m = Machine(img)
        if node_off:
            m.node_off = node_off
        m.walker(cfg[w['kind']], state=state, kind=w['kind'], x=ex)
        m.wf(POSTURE + 0x14, ey)
        m.w32(W.FIGHTERS, FT)
        m.w32(FT, TBL)
        m.w32(TBL, ENTS)
        m.w32(TBL + 8, count)
        m.uc.mem_write(ENTS + 0x1E, bytes([live]))
        m.w32(ENTS + 0xC, FACC)
        m.w32(FACC + 0x18, FPOST)
        m.w32(FACC + 0x20, FSTAT)            # step 2h: its StatusModule (+0x48 the status kind) and WorkModule
        m.w32(FACC + 0x28, FWM)
        m.w32(FWM, FWMVT)
        m.w32(FWMVT + W.WM_SET_FLOAT, WM_SETF)
        m.w32(FWMVT + W.WM_SET_INT, WM_SETI)
        out = []
        for fr in frames:
            fx, fy = fr[:2]
            if len(fr) > 2:
                m.wf(POSTURE + 0x14, fr[2])      # step 2g v3: the enemy's y this frame (a flier moves)
            m.wf(FPOST + 0x10, fx)
            m.wf(FPOST + 0x14, fy)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            if calls_out is not None:
                calls_out.append([c[1:] for c in m.calls if c[0] == 'node_gpos'])
            out.append(([c[2] for c in m.calls if c[0] == 'chgi'], [c[1:] for c in m.calls if c[0] == 'msc_status'],
                        [c[1:] for c in m.calls if c[0] == 'bi_update']))
        return out
    fall = [(3.0, 20.0), (3.0, 8.0), (3.0, 5.0), (3.0, 1.0)]
    got = stomp('kuribo', fall)
    ok = [g[0] for g in got] == [[], [], [8], []] and got[2][1] == [(FACC, (3, W.STEP_JUMP, 0))] and \
        all(g[2] == [(OBJ, INPUT)] for g in got) and not got[3][1]
    check(ok, 'fix v8: a fighter falling onto a walking Goomba (feet from above its tread box top %.2f to inside it, '
          '|dx| 3 <= %g) -> => collapses 8 and the fighter\'s StatusModule(3, 0x%X StepJump, 0); BehaviorImpl\'s '
          'update every frame %s' % (W.tread_box(byname['kuribo'])[1] + W.tread_box(byname['kuribo'])[2],
                                     W.tread_box(byname['kuribo'])[0], W.STEP_JUMP, got))
    res = {}
    res['beside'] = stomp('kuribo', [(9.0, 20.0), (9.0, 5.0)])
    res['rising'] = stomp('kuribo', [(3.0, 0.0001), (3.0, 2.0), (3.0, 5.0)])
    res['below'] = stomp('kuribo', [(3.0, 20.0), (3.0, -10.0)])     # past its bottom + the sweep (step 2g v3)
    res['first'] = stomp('kuribo', [(3.0, 5.0)])
    res['in 8'] = stomp('kuribo', fall, state=8)
    res['dead'] = stomp('kuribo', fall, state=9)
    res['not live'] = stomp('kuribo', fall, live=3)
    res['none'] = stomp('kuribo', fall, count=0)
    res['high'] = stomp('kuribo', [(3.0, 30.0), (3.0, 25.0)], ey=10.0)
    for n in ('heiho', 'waddledee', 'waddledoo', 'churine'):
        res[n] = stomp(n, fall)
    ok = all(not g[0] and not g[1] and g[2] for v in res.values() for g in v)
    hi = stomp('kuribo', [(-50.0, 40.0), (-53.0, 14.0)], ex=-50.0, ey=10.0)
    ok &= hi[1][0] == [8]
    check(ok, 'fix v8: no stomp beside it (|dx| 9), rising through it, landing past its bottom, on the first frame '
          '(no last y), in 8 / its death state, a fighter not live, no fighters, above it but not reaching its top, '
          'nor on the other walkers (no TREAD state); one on a Goomba at (-50, 10) %s' % hi[1][0])

    # ---- step 2g v3: Tiki Buzz's stomp (its tread box (6, 11.72, 1.5): the top 13.22 above its posture) -> 10 and the
    # fighter's StepJump, as the Goomba's; the test relative to the enemy and swept (a fast fall, a rising flier)
    tb = byname['tikibuzz']['tbox']
    top = 50.0 + 11.72 + tb[1] + tb[2]      # step 2g v5: the box centred on node 3 (HipN: bind height 11.72 here)
    sj = (FACC, (3, W.STEP_JUMP, 0))
    tk = {}
    tk['fall'] = stomp('tikibuzz', [(2.0, top + 7), (2.0, top + 1), (2.0, top - 1)], ey=50.0)
    tk['fast'] = stomp('tikibuzz', [(2.0, top + 7), (2.0, top + 1), (2.0, top - 5)], ey=50.0)
    tk['rising'] = stomp('tikibuzz', [(2.0, top + 7, 50.0), (2.0, top + 1, 50.0), (2.0, top + 0.5, 53.0)], ey=50.0)
    tk['beside'] = stomp('tikibuzz', [(7.0, top + 7), (7.0, top + 1), (7.0, top - 1)], ey=50.0)
    tk['through'] = stomp('tikibuzz', [(2.0, top + 7), (2.0, top + 1), (2.0, top - 10)], ey=50.0)
    tk['in 10'] = stomp('tikibuzz', [(2.0, top + 7), (2.0, top + 1), (2.0, top - 1)], state=10, ey=50.0)
    hit = lambda v: [g[0] for g in v] == [[], [], [10]] and v[2][1] == [sj] and not v[1][1]  # noqa: E731
    none = lambda v: all(not g[0] and not g[1] for g in v)  # noqa: E731
    ok = hit(tk['fall']) and hit(tk['fast']) and hit(tk['rising']) and none(tk['beside']) and none(tk['through']) \
        and none(tk['in 10'])
    # step 2g v5: the box follows the live node (the 3DS area 0 is on node 3): with HipN 3 lower and 4 to the side
    # (a bob, the model's offset) a fall onto the node's top is taken and one onto the bind height's is not; the
    # node asked is 3 of the ModelModule ([acc +0x3118]), and the Goomba (no TNODE) never asks
    ncalls = []
    ntop = 50.0 + 2.0 + tb[1] + tb[2]       # HipN 2 above the posture (9.72 below its bind height), 4 to the side
    nd = stomp('tikibuzz', [(6.0, ntop + 3), (6.0, ntop - 1)], ey=50.0, node_off=(4.0, 2.0), calls_out=ncalls)
    nb = stomp('tikibuzz', [(-3.0, ntop + 3), (-3.0, ntop - 1)], ey=50.0, node_off=(4.0, 2.0))
    gc = []
    stomp('kuribo', fall, calls_out=gc)
    ok_n = [g[0] for g in nd] == [[], [10]] and nd[1][1] == [sj] and none(nb) and \
        all(c == [(0, 3, 1)] for c in ncalls[:2]) and not any(gc)
    check(ok_n, 'step 2g v5: Tiki Buzz\'s tread box on the live node 3 (node_global_position(3, &v, 1)): HipN 9.72 '
          'below its bind height and 4 to the side -> a fall onto its top taken (below the bind box\'s top: none '
          'there), none 7 beside it (3 from the posture); node calls %s; '
          'the Goomba asks no node %s' % (ncalls[:2], gc[:1]))
    check(ok, 'step 2g v3: Tiki Buzz stomped (box top %.2f above y 50): a fall into it, a fast fall (5 a frame) past '
          'its 3-unit box, a landing while it rises 3 -> => 10 and the fighter\'s StatusModule(3, 0x%X StepJump, 0) '
          'once; none beside it (|dx| 7 > 6), through it and the sweep in one frame, nor in 10 %s'
          % (top, W.STEP_JUMP, {k: [g[0] for g in v] for k, v in tk.items()}))

    # ---- Kuribo
    I = lambda n, s: W.index(byname[n], s)  # noqa: E731,E741
    got = enters('kuribo')
    exp = {1: (8, 0, (I('kuribo', 'Fall'), 1.0, 1), ''), 2: (0, 1, (I('kuribo', 'Landing'), 1.0, 0), ''),
           3: (0xA, 1, (15, 0.6, 1), ''), 4: (5, 0, (12, 1.0, 1), ''), 5: (0xA, 1, (13, 1.0, 1), ''),
           6: (2, 1, (11, 1.0, 0), ''), 7: (2, 1, (14, 1.0, 0), ''), 8: (0, 1, (0, 1.0, 0), ''),
           9: (None, None, (1, 0.0, 0), 'bullet')}
    check(got == exp, 'kuribo enters (kinetic, ground, (motion, rate, loop)) as the 3DS\'s: %s' % got)
    # walk: the search on its first frame finds a target in front -> notice (no turn); the hop (E+0x20 = -0.4)
    wd = world('kuribo', 3, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, -50.0
    m.wf(EN + 0x20, 9.0)
    wd.run(1)
    s0 = wd.log[0]
    srch = [c for c in s0[4] if c[0] == 'search']
    ok = srch == [('search', 2, OBJ + 0x10, (10.0, 10.0, 100.0, 40.0, 0.0))] and wd.cur == 4 and \
        not [c for c in s0[4] if c[0] == 'reverse_lr'] and round(m.rf(EN + 0x20), 4) == -0.4
    # in the air (rising, then falling), lands (ground on), 30 frames after entering -> run
    m.found = -1
    m.vy, m.ground = 1.0, False
    wd.script[4] = lambda wo: setattr(wo.m, 'vy', -1.0)
    wd.script[8] = lambda wo: setattr(wo.m, 'ground', True)
    wd.run(40)
    st = wd.states()
    att = [i for i, s, _x, _st, c, _e in wd.log if s == 4 and [x for x in c if x[0] == 'attach' and x[2] == 1]]
    run_at = [i for i, s, _x, _st, _c, _e in wd.log if s == 5][:1]
    ok &= st[:3] == [3, 4, 5] and att and att[0] == 8 and run_at == [33]
    check(ok, 'kuribo: walking, search_target(search 0 {2, 100, ...}) on its first frame finds a target ahead -> '
          'notice (=> 4, no turn), the hop back (E+0x20 = -0.4, kinetic 5), ground on when it lands (frame %s), '
          'the run 30 frames after (frame %s) %s' % (att[:1], run_at, st))
    # run: input (lr, 0); every 60 run frames search 1; a target behind -> run turn -> => 5; 110 frames -> brake
    n0 = len(wd.log)
    m.found, m.target_x = 0, 300.0
    wd.run(60)
    st = wd.states(n0)
    srch = [c for e in wd.log[n0:] for c in e[4] if c[0] == 'search']
    turn_i = [e[0] for e in wd.log[n0:] if e[1] == 7][:1]
    revs = [e[0] for e in wd.log[n0:] if [c for c in e[4] if c[0] == 'reverse_lr']]
    ok = st[:3] == [5, 7, 5] and srch and srch[0][1:] == (2, OBJ + 0x10, (0.0, 10.0, 150.0, 60.0, 0.0)) and revs \
        and m.rf(OBJ + 0x10) == 1.0 and wd.log[n0][3] == (-1.0, 0.0)
    check(ok, 'kuribo: running (stick (-1, 0)), search_target(search 1 {2, 60, ...}) finds the target behind -> '
          'run turn 7 (frame %s), reverse_lr at its end (frame %s) => run 5 again %s' % (turn_i, revs[:1], st))
    m.found = -1
    n0 = len(wd.log)
    wd.run(80)
    st = wd.states(n0)
    runs = [e for e in wd.log if e[1] == 5]
    ok = st[-2:] == [6, 3] or st[-3:-1] == [6, 3]
    brk = [e[0] for e in wd.log[n0:] if e[1] == 6][:1]
    check(ok and len(runs) >= 100, 'kuribo: after 110 run frames the brake 6 (frame %s), at its end the walk 3 %s'
          % (brk, st))
    # walk: a wall ahead -> reverse_lr, walk again; a ledge: variation 0 walks on, variation 1 turns
    wd = world('kuribo', 3, lr=1.0)
    m = wd.m
    m.walls = {4}
    wd.run(2)
    ok = bool([c for c in wd.log[0][4] if c[0] == 'reverse_lr']) and \
        [c for c in wd.log[0][4] if c[0] == 'chg'][-1][2] == 3
    m.walls = set()
    wd2 = world('kuribo', 3, lr=1.0, var=0)
    wd2.m.cliff = True
    wd2.run(3)
    wd3 = world('kuribo', 3, lr=1.0, var=1)
    wd3.m.cliff = True
    wd3.run(1)
    ok &= not [c for e in wd2.log for c in e[4] if c[0] == 'reverse_lr'] and \
        bool([c for c in wd3.log[0][4] if c[0] == 'reverse_lr'])
    wd4 = world('kuribo', 3, lr=1.0)
    wd4.m.ground = False
    wd4.run(2)
    ok &= wd4.cur == 1
    check(ok, 'kuribo: a wall ahead -> reverse_lr, walk again; at a ledge variation 0 walks on, variation 1 '
          'turns; off the ground -> fall 1')
    # fall -> landing -> walk
    wd = world('kuribo', 1)
    wd.m.ground = False
    wd.script[3] = lambda wo: setattr(wo.m, 'ground', True)
    wd.run(12)
    check(wd.states()[:3] == [1, 2, 3], 'kuribo: fall 1, on the ground => landing 2, at its end -> walk 3 %s'
          % wd.states())
    # stomp: stepped on while walking => 8 (Collapses, notify_on_death), at its end -> 10; no attack armed in 8
    wd = world('kuribo', 3)
    wd.run(3)
    m = wd.m
    m.calls = []
    m.call(slots[20], {3: OBJ, 4: 0x11})
    en = [c for c in m.calls if c[0] == 'chgi']
    wd.enter(8)
    col = [c[0] for c in m.calls]
    wd.run(8)
    atk = []
    mm = Machine(img)
    mm.walker(cfg[1])
    mm.call(fn['w_atk'], {3: OBJ, 4: 8})
    atk = mm.calls
    check(en and en[0][2] == 8 and 'notify_death' in col and wd.states() == [3, 8, 10] and
          atk == [('atk_clear', ATKM)], 'kuribo: stepped on (slot 20) => collapses 8 (kinetic 0, Collapses, '
          'notify_on_death %s), at its end -> remove 10 %s; no attack in 8' % (col, wd.states()))
    # dead: kinetic flag 8 => remove
    wd = world('kuribo', 9)
    wd.run(2)
    wd.m.w32(FLAGS, 8)
    wd.run(1)
    check(wd.cur == 10, 'kuribo: dead 9 (Damage, bullet()), kinetic flag 8 => remove 10')

    # ---- Shy Guy
    got = enters('heiho')
    exp = {1: (8, 0, (8, 1.0, 1), ''), 2: (0, 1, (9, 1.0, 0), ''), 3: (2, 1, (15, 1.0, 0), ''),
           4: (1, 1, (16, 1.0, 1), ''), 5: (0, 1, (14, 1.0, 0), ''), 6: (5, 0, (16, 1.0, 1), ''),
           7: (5, 0, (12, 1.0, 1), ''), 8: (0, 1, (12, 1.0, 1), ''), 9: (3, 1, (10, 1.0, 1), ''),
           10: (0, 1, (13, 1.0, 0), ''), 12: (2, 1, (11, 1.0, 0), ''), 13: (2, 1, (13, 0.7, 0), ''),
           14: (21, 0, (8, 1.0, 1), ''), 15: (None, None, (3, 0.0, 0), 'bullet')}
    check(got == exp, 'heiho enters (kinetic, ground, (motion, rate, loop)) as the 3DS\'s: %s' % got)
    # walk energy row, kick, the walk timer -> wait (Wait twice) -> walk
    wd = world('heiho', 4, lr=-1.0)
    m = wd.m
    walk_en = {o: round(m.rf(EN + o), 4) for o in (8, 0x10, 0x14, 0x20, 0x24, 0x28, 0x2C)}
    t = m.r32(OBJ + W.V(1))
    wd.run(t + 40)
    st = wd.states()
    ok = walk_en == {8: 0.3, 0x10: 0.3, 0x14: 0.0, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5} and 60 <= t <= 120
    ok &= st[:3] == [4, 3, 4] or st[:2] == [4, 3]
    waits = [c for e in wd.log for c in e[4] if c[0] == 'motion' and c[2] == 15]
    check(ok and len(waits) == 1, 'heiho: walk (energy %s, kick), %d frames -> wait 3 (Wait, again once), -> walk '
          '4 %s' % (walk_en, t, st))
    # search -> notice (two hops in place) -> hold -> run (the run row) -> brake -> settle -> walk
    wd = world('heiho', 4, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, 50.0
    wd.run(31)
    air(wd)
    wd.run(1)
    ok = wd.cur == 7 and bool([c for e in wd.log for c in e[4] if c[0] == 'reverse_lr'])
    srch = [c for e in wd.log for c in e[4] if c[0] == 'search'][:1]
    ntc = {o: round(m.rf(EN + o), 4) for o in (0x1C, 0x20, 0x24, 0x28, 0x2C)}
    ok &= ntc == {0x1C: 0.0, 0x20: 0.0, 0x24: 2.0, 0x28: 0.0, 0x2C: 2.0}
    m.found = -1
    hops = []
    for _ in range(14):
        wd.frame()
        h = [c for c in wd.log[-1][4] if c[0] == 'kinetic' and c[2] == 5]
        if h:
            air(wd)
        hops += h
    ok &= wd.cur in (8, 9) and len(hops) == 1
    n0 = len(wd.log)
    wd.run(3)
    run_en = {o: round(m.rf(EN + o), 4) for o in (8, 0x10, 0x14, 0x20, 0x24, 0x28, 0x2C)}
    ok &= wd.cur == 9 and 60 <= m.r32(OBJ + W.V(2)) <= 80 and \
        run_en == {8: 0.8, 0x10: 0.8, 0x14: 0.0075, 0x20: 0.5, 0x24: 2.5, 0x28: 0.5, 0x2C: 2.5}
    check(ok, 'heiho: walking, search_target(search 0) %s finds the target behind: reverse_lr, -> notice 7 '
          '(set_kinetic_jump(0, 2.0): E %s), a second hop on landing, => hold 8, -> run 9 (the run row %s, 80 '
          'frames)' % (srch, ntc, run_en))
    n0 = len(wd.log)
    wd.run(100)
    st = wd.states(n0)
    ok = st[:3] == [9, 12, 14]
    m.w32(FLAGS, 1)
    wd.run(3)
    check(ok and wd.cur == 4, 'heiho: after 80 run frames the brake 12, at its end (stopped) the settle 14 (kinetic '
          '21), kinetic flag 1 -> walk 4 %s' % wd.states(n0))
    # run: a target behind -> run turn 13 => run; a wall -> wall run turn 10 => run
    wd = world('heiho', 9, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, 50.0
    wd.run(40)
    st = wd.states()
    ok = st[:3] == [9, 13, 9]
    m.found = -1
    m.walls = {2, 4}
    n0 = len(wd.log)
    wd.run(2)
    m.walls = set()
    wd.run(10)
    ok &= wd.states(n0)[:3] == [9, 10, 9]
    check(ok, 'heiho: running, the target behind (search 1) -> run turn 13 (RunTurn at 0.7) => run; a wall -> '
          'wall run turn 10 => run %s %s' % (st, wd.states(n0)))
    # walk: a wall -> hop 6; landing on the same height => turn 5 => walk; higher, no wall => landing 2
    for dy, want in ((0.0, [4, 6, 5, 4]), (8.0, [4, 6, 2])):
        wd = world('heiho', 4, lr=1.0)
        m = wd.m
        m.walls = {4}
        wd.run(1)
        m.walls = set()
        air(wd)
        wd.script[wd.i + 2] = lambda wo, dy=dy: wo.m.wf(POSTURE + 0x14, dy)
        wd.run(14)
        check(wd.states()[:len(want)] == want, 'heiho: a wall -> wall hop 6 (kinetic 5, Walk); landed %s => %s %s'
              % ('on the same height' if not dy else '%g higher' % dy, want[2:], wd.states()))

    # ---- Waddle Dee
    got = enters('waddledee')
    exp = {1: (8, 0, (8, 1.0, 1), ''), 2: (None, 0, (11, 1.0, 1), ''), 3: (0, 1, (10, 1.0, 0), ''),
           4: (1, 1, (13, 1.2, 1), ''), 5: (0, 1, (12, 1.0, 0), ''), 6: (5, 0, (9, 1.0, 0), ''),
           7: (None, None, (0, 0.0, 0), 'bullet')}
    check(got == exp, 'waddledee enters as the 3DS\'s (step 2j: the parasol fall in the aerial module, no kinetic '
          'change, ParasolFall): %s' % got)
    wd = world('waddledee', 4, lr=-1.0)
    m = wd.m
    wd.run(300)
    jumps = [e[0] for e in wd.log if e[1] == 6]
    stamp = [e[0] for e in wd.log if e[1] == 4]
    ok = not [c for e in wd.log for c in e[4] if c[0] == 'search']
    ok &= all(not [c for c in e[4] if c[0] in ('atk_create',)] for e in wd.log)
    check(ok and len(stamp) > 250, 'waddledee: walks (no search: it never chases)%s' %
          (', jumps on frames %s' % jumps[:3] if jumps else ''))
    for var, want in ((0, [4, 6, 2]), (2, [4, 6, 1])):
        wd = world('waddledee', 4, lr=-1.0, var=var)
        m = wd.m
        m.walls = {2}
        jumped = False
        for _ in range(40):
            wd.frame()
            if wd.cur == 6 and not jumped:
                jumped = True
                m.walls = set()
                m.vy, m.ground = 1.0, False
                wd.script[wd.i + 2] = lambda wo: setattr(wo.m, 'vy', -1.0)
                wd.script[wd.i + 4] = lambda wo: setattr(wo.m, 'ground', True)
            if wd.cur == 5:
                m.walls = set()
        st = wd.states()
        ok = st[:3] == want or (st[:2] == [4, 5] and 4 in st[2:])
        check(ok, 'waddledee (variation %d): a wall -> 50 %% jump 6 (else turn 5); from the apex %s; lands 3 -> 4 %s'
              % (var, 'the parasol fall 2' if var <= 1 else 'the fall 1', st))
    wd = world('waddledee', 4, lr=-1.0, var=0)
    wd.m.ground = False
    wd.run(1)
    wd3 = world('waddledee', 4, lr=-1.0, var=2)
    wd3.m.ground = False
    wd3.run(1)
    check(wd.pending == 2 and wd3.pending == 1, 'waddledee: off the ground -> 2 (variations 0 / 1) / 1')

    # ---- Waddle Doo
    got = enters('waddledoo')
    exp = {1: (8, 0, (10, 1.0, 1), ''), 2: (0, 1, (12, 1.0, 0), ''), 3: (1, 1, (14, 1.0, 1), ''),
           4: (0, 1, (13, 1.0, 0), ''), 5: (5, 0, (11, 1.0, 0), ''), 6: (None, None, (2, 0.0, 0), 'bullet'),
           8: (15, 0, (10, 0.0, 0), ''), 9: (5, 0, (11, 1.0, 0), ''),     # step 2j: 9 the random hop (3DS 6)
           10: (0, 1, (1, 1.0, 0), ''), 11: (None, None, (0, 4.0, 0), '')}  # step 2k: the beam (3DS 7 / 8)
    check(got == exp, 'waddledoo enters as the 3DS\'s: %s' % got)
    wd = world('waddledoo', 3, lr=-1.0)
    m = wd.m
    m.found, m.target_x = 0, 50.0
    m.w32(OBJ + W.V(4), 0xFFFFFC18)       # step 2j: the random hop's counter held back (tested in smashrun_step2j_test)
    wd.run(70)
    st = wd.states()
    srch = [c for e in wd.log for c in e[4] if c[0] == 'search'][:1]
    ok = st[:3] == [3, 4, 3] and srch == [('search', 2, OBJ + 0x10, (0.0, 0.0, 200.0, 200.0, 0.0))]
    check(ok, 'waddledoo: walks, every 60 frames search_target(search 0) finds the target behind -> turn 4 => walk '
          '%s' % st)
    wd = world('waddledoo', 3, lr=1.0)
    m = wd.m
    m.walls = {4}
    wd.run(1)
    m.walls = set()
    air(wd)
    wd.run(14)
    check(wd.states()[:4] == [3, 5, 4, 3], 'waddledoo: a wall -> jump 5; landed on the same height => turn 4 => '
          'walk %s' % wd.states())

    # ---- Churine
    got = enters('churine')
    exp = {1: (8, 0, (12, 1.0, 1), ''), 2: (0, 1, (8, 1.0, 0), ''), 3: (1, 1, (11, 1.0, 1), ''),
           4: (5, 0, (7, 1.0, 1), ''), 5: (0, 1, (10, 1.0, 0), ''), 6: (None, None, (2, 0.0, 0), 'bullet'),
           8: (5, 0, (7, 1.0, 0), ''), 9: (0, 1, (9, 1.0, 0), '')}     # step 2k: the hop / the powder (3DS 6 / 7)
    check(got == exp, 'churine enters as the 3DS\'s: %s' % got)
    wd = world('churine', 3, lr=1.0)
    m = wd.m
    m.target = -1
    m.walls = {4}
    wd.run(1)
    m.walls = set()
    air(wd)
    wd.script[wd.i + 2] = lambda wo: wo.m.wf(POSTURE + 0x14, 30.0)
    wd.run(14)
    st = wd.states()
    m.cliff = True
    n0 = len(wd.log)
    wd.run(2)
    check(st[:4] == [3, 4, 2, 3] and wd.states(n0)[:2] == [3, 5], 'churine: a wall -> jump 4 (initialize first); '
          'landed 30 higher, no wall => landing 2 (no look back) -> walk 3; a ledge -> turn 5 %s %s'
          % (st, wd.states(n0)))
    # no kind searches for a contact attack in its walk: set_attack_data is per state (above)

    # ---- step 2c: the White Bear (enemy_fs.cro 0x7E378-0x7F318)
    got = enters('whitebear')
    exp = {1: (8, 0, (7, 1.0, 1), ''), 2: (0, 1, (8, 1.0, 0), ''), 3: (1, 1, (9, 1.0, 1), ''),
           4: (0, 1, (14, 1.0, 0), ''), 5: (0, 1, (15, 1.0, 0), ''), 6: (0, 1, (11, 1.5, 0), ''),
           7: (5, 0, (13, 1.0, 0), ''), 8: (5, 0, (10, 1.0, 0), ''), 9: (0, 1, (12, 1.0, 0), ''),
           10: (None, None, (2, 0.0, 0), 'bullet')}
    check(got == exp, 'whitebear enters (kinetic, ground, (motion, rate, loop)) as the 3DS\'s: %s' % got)
    # walk: input (lr, 0), the walk timer random(60, 120) set; a search with group 1 once the counter passes its
    # interval (60): found -> quake hold 6 -> (motion end) jump 7 -> (falling) 8 -> (ground) => landing quake 9
    wd = world('whitebear', 3, lr=-1.0)
    m = wd.m
    wd.enter(3)
    t = m.r32(OBJ + W.V(1))
    ok = 60 <= t <= 120 and m.r32(OBJ + W.V(0)) == 0
    m.found = 0
    wd.run(62)
    srch = [(e[0], c) for e in wd.log for c in e[4] if c[0] == 'search']
    ok &= wd.log[0][3] == (-1.0, 0.0) and len(srch) == 1 and srch[0][0] == 60 and \
        srch[0][1][1:] == (2, OBJ + 0x10, (0.0, 10.0, 180.0, 140.0, 0.0)) and wd.cur == 6
    check(ok, 'whitebear: walking (stick (-1, 0), walk timer %d in 60..120), search_target(group 1 {2, 60, 180, '
          '140, 0, 10}) on the frame its counter passes 60 (frame %s) -> quake hold 6' % (t, srch[:1] and srch[0][0]))
    m.found = -1
    m.vy = 1.0
    n0 = len(wd.log)
    wd.run(7)
    up = [e for e in wd.log[n0:] if e[1] == 7]
    en7 = [c for e in wd.log[n0:] for c in e[5] if c[0] == 'kick2']
    ok = wd.cur == 7 and en7 == [('kick2', KIN, 0x20000004)] and round(m.rf(EN + 0x24), 3) == 1.5 and \
        round(m.rf(EN + 0x2C), 3) == 1.5 and round(m.rf(EN + 0x3C), 3) == 0.1 and m.rf(EN + 0x20) == 0.0
    check(ok, 'whitebear: at QuakeHold\'s end (in view: the camera test is not ported) -> quake jump 7: E+0x24 / '
          '+0x2C = 1.5, +0x3C = 0.1, +0x20 / +0x28 = 0, the kick vt+0xEC(0x20000004), kinetic 5 %s' % en7)
    m.vy, m.ground = -1.0, False
    wd.run(3)
    ok = wd.cur == 8 and round(m.rf(EN + 0x2C), 3) == 3.0 and round(m.rf(EN + 0x3C), 3) == 1.0
    m.ground = True
    wd.run(1)
    ok &= wd.cur == 9 and m.r32(OBJ + W.V(4)) == 1
    check(ok, 'whitebear: speed y <= 0 -> quake fall 8 (E+0x2C = 3, +0x3C = 1); on the ground (under 180 frames) '
          '=> quake landing 9 (V4 = 1) %s' % wd.states(n0))
    # the landing's end: 50 %% -> jump again (7) or the walk (3) with the search cool-down 60; run many to see both
    outs = {}
    for seed in range(40):
        wd2 = world('whitebear', 9)
        wd2.m.w32(D['consts'] + 8, 0x1234567 + seed * 7919)
        wd2.m.w32(OBJ + W.V(4), 0)
        wd2.enter(9)
        wd2.run(8)
        nxt = [st for st in wd2.states() if st != 9][:1]
        outs.setdefault(tuple(nxt), 0)
        outs[tuple(nxt)] += 1
        if nxt == [3]:
            in3 = len([e for e in wd2.log if e[1] == 3])
            ok3 = wd2.m.r32(OBJ + W.V(2)) + in3 == 60       # 60, less the walk frames since
    check(set(outs) == {(7,), (3,)} and ok3, 'whitebear: at the landing\'s end, V4 1 < 3: success_by_percent(50) -> '
          'jump again 7, else the walk 3 with the search cool-down 60 %s' % outs)
    wd2 = world('whitebear', 9)
    wd2.m.w32(OBJ + W.V(4), 2)
    en = wd2.enter(9)
    rate = [c[4] for c in en if c[0] == 'motion']
    wd2.run(8)
    ok = rate == [0.5] and wd2.states()[1:2] == [3]
    wd2 = world('whitebear', 9)
    wd2.m.w32(OBJ + W.V(4), 1)
    outs = set()
    for seed in range(60):
        wd2 = world('whitebear', 9)
        wd2.m.w32(D['consts'] + 8, 0x7654321 + seed * 104729)
        wd2.m.w32(OBJ + W.V(4), 1)
        wd2.enter(9)
        wd2.run(8)
        outs.add(tuple([st for st in wd2.states() if st != 9][:1]))
    check(ok and outs == {(7,), (3,)}, 'whitebear: a repeated landing plays QuakeLanding at 0.5; after the third '
          'quake the walk 3 always; after the second 25 %% %s' % outs)
    # cool-down: no search for 60 frames after a quake; the walk timer -> special turn 4 -> reverse_lr => 3
    wd = world('whitebear', 3)
    m = wd.m
    m.found = 0
    wd.enter(3)
    m.w32(OBJ + W.V(2), 60)
    m.w32(OBJ + W.V(1), 1000)
    wd.run(125)
    srch = [e[0] for e in wd.log for c in e[4] if c[0] == 'search']
    ok = srch == [60]
    wd = world('whitebear', 3)
    wd.enter(3)
    wd.m.w32(OBJ + W.V(1), 3)
    wd.run(12)
    revs = [e[0] for e in wd.log if [c for c in e[4] if c[0] == 'reverse_lr']]
    ok &= wd.states()[:3] == [3, 4, 3] and bool(revs)
    check(ok, 'whitebear: the search cool-down (V2 60) skips the searches (first at frame %s); the walk timer runs '
          'out -> special turn 4, reverse_lr at its end => walk 3 %s' % (srch, wd.states()))
    wd = world('whitebear', 3, lr=1.0)
    wd.enter(3)
    wd.m.walls = {4}
    wd.run(1)
    a = wd.states() + [wd.pending]
    wd = world('whitebear', 3, lr=1.0)
    wd.enter(3)
    wd.m.cliff = True
    wd.run(1)
    b = [wd.pending]
    wd = world('whitebear', 3, lr=1.0)
    wd.enter(3)
    wd.m.ground = False
    wd.run(1)
    c_ = [wd.pending]
    check(a[-1] == 5 and b == [5] and c_ == [1], 'whitebear: a wall or a ledge ahead -> turn 5; off the ground -> '
          'fall 1')
    # a long fall (180 frames or more since the jump) lands in the plain landing 2
    wd = world('whitebear', 8)
    wd.m.w32(OBJ + W.V(5), 179)
    wd.m.ground = True
    wd.run(1)
    check(wd.cur == 2, 'whitebear: on the ground after >= 180 frames in the jump => landing 2 (no quake)')

    # ---- step 2c: the Gordo (enemy_fs.cro 0x19CB0-0x1A470): spins in place; its contact attack in state 1 (above)
    got = enters('gordo')
    wd = world('gordo', 1)
    wd.run(20)
    check(got == {1: (0xFFFFFFFF, 0, (0, 1.0, 1), '')} and wd.states() == [1] and
          not [c for e in wd.log for c in e[4]], 'gordo: state 1 kinetic -1, ground off, Togetoge loop; its update '
          'changes nothing (home energy not ported) %s' % got)

    # ---- step 2c v2: the White Bear's landing quake (the 3DS 0x7EE74): request_quake, the absolute hit on the first
    # fighter on the ground (AttackModule MSC 0x2716 set_abs, 0x271D hit_absolute), the effects
    FT2, TBL2, ENTS2 = HEAP + 0x36000, HEAP + 0x36100, 0x32000000
    FACC = [HEAP + 0x38000 + 0x100 * i for i in range(4)]

    def landing(sits, count=3, live=(4, 4, 4, 4)):
        m = Machine(img)
        m.uc.mem_map(ENTS2, 0x20000)
        m.walker(cfg[0x40], state=9, kind=0x40, x=10.0)
        m.wf(POSTURE + 0x14, 5.0)
        m.wf(POSTURE + 0x18, 0.0)
        m.w32(W.FIGHTERS, FT2)
        m.w32(FT2, TBL2)
        m.w32(TBL2, ENTS2)
        m.w32(TBL2 + 8, count)
        for i in range(4):
            e = ENTS2 + W.FIGHTER_ENTRY * i
            m.uc.mem_write(e + 0x1E, bytes([live[i]]))
            m.w32(e + 0xC, FACC[i])
            m.w32(FACC[i], 0x00010000 * (i + 1) + 0x42)          # the object id at the accessor's +0
            m.situation[FACC[i]] = sits[i]
        m.call(rows['whitebear'][9][0], {3: OBJ})
        return m.calls
    calls = landing((2, 0, 0, 2))
    seq = [c[0] for c in calls if c[0] in ('kinetic', 'attach', 'motion', 'quake', 'atk_msc', 'effect', 'effect0')]
    msc = [c for c in calls if c[0] == 'atk_msc']
    eff = [c for c in calls if c[0] in ('effect', 'effect0')]
    sit = [c[1] for c in calls if c[0] == 'msc_status']
    absw = tuple(W.word(v) for v in W.ABS_WORDS)
    check(seq == ['kinetic', 'attach', 'motion', 'quake', 'atk_msc', 'atk_msc', 'effect', 'effect0'] and
          [c for c in calls if c[0] == 'quake'] == [('quake', OBJ, W.QUAKE_KIND)] and sit == FACC[:2] and
          msc == [('atk_msc', ATKM, absw), ('atk_msc', ATKM, (0x271D, 0, 0, 0x00020042, 0, 0))] and
          eff == [('effect', OBJ, 0x7400000, (10.0, 5.0, 0.0), (0.0, 0.0, 0.0), 2.5),
                  ('effect0', OBJ, 0x7400001, (0.0, 0.0, 0.0), 8.0)],
          'whitebear landing (9): request_quake(%d), the first fighter on the ground (slot 1: slot 0 in the air) '
          'gets set_abs %s + hit_absolute(object id 0x20042), effects 0x7400000 at its feet (2.5) and 0x7400001 (8)'
          % (W.QUAKE_KIND, [hex(x) for x in absw]))
    c1 = landing((2, 2, 2, 2))
    c2 = landing((0, 0, 0, 0), live=(3, 3, 4, 4), count=2)
    c3 = landing((2, 2, 2, 0), count=4)
    c4 = landing((2, 2, 2, 0), count=3)
    m0 = [c for c in c1 if c[0] == 'atk_msc']
    m2 = [c for c in c2 if c[0] == 'atk_msc']
    m3 = [c[2][3] for c in c3 if c[0] == 'atk_msc' and c[2][0] == 0x271D]
    m4 = [c for c in c4 if c[0] == 'atk_msc']
    check(not m0 and not m2 and m3 == [0x40042] and not m4 and [c[0] for c in c1 if c[0] in ('effect', 'effect0')]
          == ['effect', 'effect0'], 'whitebear landing: no hit when nobody is on the ground, when the grounded fighters '
          'are not live or past the table\'s count; slot 3 when it is the only one; the effects always')
    # damage: the absolute set_abs words: damage 10, angle 90, kbg 100, wbkb 0, bkb 40 (P6)
    check(W.ABS_WORDS[:8] == (0x2716, 0, 0, 10.0, 90, 100, 0, 40) and len(W.ABS_WORDS) == 18,
          'whitebear: set_abs words (op, kind, part, damage 10, angle 90, kbg 100, wbkb 0, bkb 40, ... 18 words)')

    # ---- step 2c v2: Waddle Doo's leave (the 3DS's state 9): 600 walk frames -> leave 8 -> 300 frames -> remove 7
    m = Machine(img)
    m.walker(cfg[0x19], state=0, kind=0x19)
    m.target, m.target_x = 0, -300.0
    m.call(fn['w_start'], {3: OBJ})
    ok = m.r32(OBJ + W.V(7)) == 600
    wd = world('waddledoo', 3, lr=-1.0)
    wd.m.w32(OBJ + W.V(7), 3)
    wd.m.found = -1
    wd.run(4)
    en = wd.log[-1][5] if wd.cur == 8 else []
    ok &= wd.states()[:2] == [3, 8]
    fol = [c for c in en if c[0] == 'follow']
    mot = [(c[2], c[4], c[5]) for c in en if c[0] == 'motion']
    ok &= fol == [('follow', OBJ, 0x8000005, 0, (0.0, 3.0, 0.0), (0.0, 0.0, 0.0), 0.85)] and mot == [(10, 0.0, 0)]
    ok &= [c[2] for c in en if c[0] == 'kinetic'] == [15] and [c[2] for c in en if c[0] == 'attach'] == [0] and \
        [c[2] for c in en if c[0] == 'set_correct'] == [0] and round(wd.m.rf(EN + 0x30), 3) == -0.02 and \
        round(wd.m.rf(EN + 0x34), 3) == 30.0 and wd.m.r32(OBJ + W.V(6)) == 299   # 300, one update run
    wd.run(301)
    rm = [c for e in wd.log for c in e[4] if c[0] == 'remove_effect']
    ok &= wd.states()[-1] == 7 and rm == [('remove_effect', OBJ, 0x7777)] and wd.m.r32(OBJ + W.DEFEATED) == 0
    check(ok, 'waddledoo: start sets the leave timer 600; walking it counts down, at 0 -> leave 8 (Fall at rate 0, '
          'energy +0x30 -0.02 / +0x34 30, kinetic 15, ground off, set_correct(0), the leave effect 0x8000005 at '
          'node 0 (0, 3, 0) x 0.85), after 300 frames the effect removed -> remove 7 (not defeated) %s'
          % wd.states())
    wd = world('waddledoo', 6)
    ok = wd.m.r32(OBJ + W.DEFEATED) == 1
    wd2 = world('kuribo', 8)
    check(ok and wd2.m.r32(OBJ + W.DEFEATED) == 1, 'v2: the death state and the Goomba\'s collapse set DEFEATED (the '
          'removal then plays the defeat effect and drops items)')

    # T2 / S2
    t1 = [img.u32(W.MOTION_SETS + 4 * k) for k in range(0x61)]
    sets2a = E.build_sets(img)
    for stage in (0x94, 0x10):
        m = Machine(img)
        m.stage(stage)
        m.w32(MGR + 0x5EC, 2)
        m.run(E.SITE_T, W.SITE_T + 8, {31: MGR, 0: 0})
        got = [m.r32(W.MOTION_SETS + 4 * k) for k in range(0x61)]
        exp = list(t1)
        if stage == 0x94:
            for name, k, _t, _c in E.PAIRS:
                exp[k] = sets2a[name][0]
            for w in W.WALKERS:
                exp[w['kind']] = D['set_' + w['name']]
        ok = got == exp and m.uc.reg_read(R[0]) == 2 and m.uc.reg_read(UC_PPC_REG_PC) == W.SITE_T + 8
        if stage == 0x94:
            r = []
            for k in W.KINDS:
                m.uc.reg_write(UC_PPC_REG_LR, DONE)
                m.run(0x02DC6D68, DONE, {3: k})
                r.append(m.uc.reg_read(R[3]))
            ok &= r == [D['set_' + w['name']] for w in W.WALKERS]
        check(ok, 'T2 (stage 0x%X): %s' % (stage, 'the walkers\' sets (2a\'s four kept), get_motion_data_set returns '
                                            'them' if stage == 0x94 else 'the table unchanged'))
    for stage, pm in ((0x94, PM), (0x10, PM), (0x94, 0)):
        m = Machine(img)
        m.stage(stage)
        m.w32(E.PARAM_MGR, pm)
        m.uc.mem_write(PM + W.SLOTS, struct.pack('>97I', *[0x50000000 + i for i in range(0x61)]))
        m.w32(MGR + 0x5EC, 2)
        before = [m.r32(PM + W.SLOTS + 4 * k) for k in range(0x61)]
        m.run(E.SITE_S, W.SITE_S + 4, {3: 0x10AB0000, 28: MGR, 31: 7})
        after = [m.r32(PM + W.SLOTS + 4 * k) for k in range(0x61)]
        exp = list(before)
        if stage == 0x94 and pm:
            for _n, k, twin, _c in E.PAIRS:
                exp[k] = before[twin]
            for w in W.WALKERS:                # step 2l: every kind its own static param object (2k: the Doo's)
                exp[w['kind']] = D[W.param_label(w['name'])]
        # step 2k: r3 is not live after the hook (0x02D9A62C / 0x02D9A6AC set it): k2_twins (its own test) uses it
        check(after == exp and m.uc.reg_read(R[0]) == 2 and
              m.uc.reg_read(R[1]) == STACK and m.uc.reg_read(R[28]) == MGR,
              'S2 (stage 0x%X%s): %s' % (stage, '' if pm else ', no param manager',
                                         'slot[K] = the kind\'s own param object for the walkers (2a\'s kept), r0 / r1 / r28 kept'
                                         if stage == 0x94 and pm else 'no slot changed'))

    # the sets
    pac_stems = {}
    if root:
        import omo
        for w in W.WALKERS:
            pac = os.path.join(root, 'motion', 'enemy', w['name'], 'body', 'main.pac')
            pac_stems[w['name']] = [n[:-4] for n, _d in omo.pac_read(pac) if n.endswith('.omo')]
    for w in W.WALKERS:
        n, s = w['name'], D['set_' + w['name']]
        ms = w['motions']
        head = [img.u32(s + 4 * i) for i in range(6)]
        ents = [(img.u32(s + 0x18 + 8 * i), img.u32(s + 0x1C + 8 * i)) for i in range(len(ms))]
        ok = head == [s + 0x18, len(ms), 0, 0, 0, 0] and ents == [(zlib.crc32(W.stem(n, sfx).encode(), 0xFFFFFFFF), f)
                                                                 for sfx, f in ms]
        hs = D.get('hs_' + n)
        if hs:
            ok &= [img.u32(hs + 4 * i) for i in range(3 * len(ms))] == (list(w['hs3ds']) if w.get('hs3ds') else
                [zlib.crc32((sfx.lower() + x).encode()) for sfx, _f in ms for x in ('.init', '', '.exit')])
        check(ok, 'set %s (0x%08X): %d entries, K\'s 3DS order, crc32(stem, 0xFFFFFFFF), flags%s'
              % (n, s, len(ms), '; hashsets 0x%08X' % hs if hs else '; no hashsets (none on the 3DS)'))
        if root:
            have = {zlib.crc32(x.encode(), 0xFFFFFFFF) for x in pac_stems[n]}
            missing = [W.stem(n, sfx) for (sfx, _f), (h, _f2) in zip(ms, ents) if h not in have]
            check(not missing, 'set %s: every entry is an OMO of %s/body/main.pac (%d) %s'
                  % (n, n, len(pac_stems[n]), missing))
            hashes = {img.u32(hs + 4 * i) for i in range(3 * len(ms))} if hs else set()
            for f in ('attack', 'effect', 'sound'):
                p = os.path.join(root, 'animcmd', 'enemy', n, f + '.bin')
                if os.path.exists(p):
                    dd = open(p, 'rb').read()
                    cnt = struct.unpack('>I', dd[8:12])[0]
                    scr = [struct.unpack('>I', dd[0x10 + 8 * i:0x14 + 8 * i])[0] for i in range(cnt)]
                    out = [hex(h) for h in scr if h not in hashes]
                    check(not out, 'set %s: %s.bin\'s %d scripts are in its hashsets %s' % (n, f, cnt, out))
    overrun_check()
    print('%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
