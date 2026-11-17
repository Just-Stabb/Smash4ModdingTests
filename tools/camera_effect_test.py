#!/usr/bin/env python3
"""Unicorn test of tools/camera_effect_cave.py (Effect_Camera) on an executable with exe_v46y_hold's patches:

  python3 tools/camera_effect_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). Run with the game's own code around
the hooks:
  - the command tables (the game's CRC search, both script loaders, the handler fetch) for Effect_Camera and every
    earlier cave's commands (acmd_ext's, Line_Test, Var_Reset_Set, Hitbox_Hold);
  - Effect_Camera's handler on a fighter-like object (EffectModule at accessor +0xA0 with the game's vtable, its world
    request vt +0x44 replaced by a recording stub that makes an instance in a fake effect manager's pool), with the
    camera table (0x10573CC0) holding a camera snapshot: the game's own look-at / inverse (0x03349A38), tanf
    (0x04ADE970) and rotation builder (0x033730A0) run (their paired-single saves nopped: unicorn can't run them);
  - the calc pass's hook (0x032EFD04 -> cf_calc -> back at 0x032EFD08 with the pass's own first instruction done):
    the camera moved / zoomed, Frames running out (the game's kill facade replaced by a recording stub), an effect
    that ends or whose slot is reused, no camera, the 17th effect;
  - the game's own instance update (0x0334E0C8, up to where it has the matrix it gives eft): with the cave's flag
    0x8000 it takes +0x50 as the cave wrote it; without it, it rebuilds +0x50 from the instance's position / rotation /
    scale (what the cave's flag turns off).
Every matrix is checked against camera_effect_cave.matrix() (the Python reference: look-at from eye / target / up).
"""
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import camera_effect_cave as CF  # noqa: E402
import line_test_cave as LT  # noqa: E402
import acmd_ext_test  # noqa: E402
from acmd_ext_test import check, r32, w32, run, RET, CRC_TABLE, COUNT, SIZES, HANDLERS, BUF  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn import UcError  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_0, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5,  # noqa: E402
                               UC_PPC_REG_6, UC_PPC_REG_7, UC_PPC_REG_12, UC_PPC_REG_29, UC_PPC_REG_LR, UC_PPC_REG_PC)

REG = lambda n: UC_PPC_REG_0 + n          # noqa: E731
ACC, EM, PARAMS, STATE, FLAG = 0x7F001000, 0x7F001200, 0x7F001400, 0x7F001600, 0x7F001700
SRC, REC, KREC = 0x7F001800, 0x7F002400, 0x7F002500
STUB = 0x04BE3000                         # the stubs: in the emulated code space past the cave (in branch reach)
MGR_FAKE = 0x7F100000                     # a fake effect manager: pool at +0x4040 (100 x 0x1C0)
TOL = 2e-4


def fb(v):
    return struct.unpack('>I', struct.pack('>f', v))[0]


def rf(mu, a, n):
    return list(struct.unpack('>%df' % n, mu.mem_read(a, 4 * n)))


def wf(mu, a, vals):
    mu.mem_write(a, struct.pack('>%df' % len(vals), *vals))


def close(a, b, tol=TOL):
    fa = [x for row in a for x in (row if isinstance(row, (list, tuple)) else [row])]
    fb_ = [x for row in b for x in (row if isinstance(row, (list, tuple)) else [row])]
    return len(fa) == len(fb_) and all(abs(x - y) <= tol * max(1, abs(y)) for x, y in zip(fa, fb_))


def ensure(mu, lo, hi):
    """map [lo, hi) page by page where not mapped yet"""
    mapped = [(b, e) for b, e, _p in mu.mem_regions()]
    a = lo & ~0xFFF
    while a < hi:
        if not any(b <= a <= e for b, e in mapped):
            mu.mem_map(a, 0x1000)
        a += 0x1000


def main():
    exe = sys.argv[1]
    orig = CF.rpx_reader(exe)
    words, lab, s = CF.build(orig)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    check('present() on the patched words', CF.present(lambda x: words.get(x, orig(x))), True)
    check('present() on the unpatched exe', CF.present(orig), False)
    try:
        CF.build(lambda x: words.get(x, orig(x)))
        check('building over itself refused', False, True)
    except AssertionError:
        check('building over itself refused', True, True)
    check('the cave inside its region, the rest of it zero', (min(words) >= 0x02000000,
          max(a for a in words if a >= CF.CAVE) < CF.LIMIT), (True, True))
    others = [a for a in words if not CF.CAVE <= a < CF.LIMIT]
    check('words outside the cave: the calc hook and the 4 command-table fallbacks',
          sorted(others) == sorted([CF.CALC_AT, s['lk_none'], s['s1'], s['s2'], s['f']]), True)

    # ---- command tables
    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    check('Effect_Camera CRC not a game command', CF.CMD_CRC in dict(pairs), False)
    check('Effect_Camera CRC not an acmd_ext command', CF.CMD_CRC in [C.crc(c[0]) for c in C.COMMANDS], False)

    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    check('vanilla CRCs keep their index', [hex(c) for c, i in pairs[::7] if lookup(pm, c) != i], [])
    check('acmd_ext CRCs keep theirs', [lookup(pm, C.crc(c[0])) for c in C.COMMANDS],
          [C.NEW_BASE + k for k in range(len(C.COMMANDS))])
    earlier = {n: zlib.crc32(n.encode()) & 0xFFFFFFFF for n in ('Line_Test', 'Var_Reset_Set', 'Hitbox_Hold')}
    check('earlier caves\' commands (Line_Test, Var_Reset_Set, Hitbox_Hold) keep their index',
          [lookup(pm, c) for c in earlier.values()], [lookup(om, c) for c in earlier.values()])
    check('... which the unpatched exe has (1096, 2000, 2100)', [lookup(om, c) for c in earlier.values()],
          [1096, 2000, 2100])
    check('Effect_Camera -> its index', lookup(pm, CF.CMD_CRC), CF.CF_INDEX)
    check('unknown CRC -> -1', lookup(pm, 0x12345678), 0xFFFFFFFF)
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    script = [0xB738EABD, CF.CMD_CRC, 0x42ACFE7D, earlier['Line_Test'], earlier['Hitbox_Hold'], CF.CMD_CRC]
    want_idx = [idx[0xB738EABD], CF.CF_INDEX, idx[0x42ACFE7D], 1096, 2100, CF.CF_INDEX]
    want_size = [size[want_idx[0]], 12, size[want_idx[2]], 11, 3, 12]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {REG(28): BUF, UC_PPC_REG_29: 0, REG(30): len(script),
                                      UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {REG(28): BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script),
                                      REG(30): SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, sz in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += sz
        run(pm, start, stop, regs)
        check('loader %d: indices (Hitbox, Effect_Camera, FRAME, Line_Test, Hitbox_Hold, Effect_Camera)' % (loop + 1),
              [r32(pm, BUF + 4 * x) for x in offs], want_idx)
        check('loader %d: words stepped' % (loop + 1), pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4),
              sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0)
    check('vanilla handlers unchanged', [i for _, i in pairs[::11] if fetch(pm, i) != r32(om, HANDLERS + 4 * i)], [])
    check('acmd_ext handlers unchanged', [fetch(pm, C.NEW_BASE + k) for k in range(len(C.COMMANDS))],
          [fetch(om, C.NEW_BASE + k) for k in range(len(C.COMMANDS))])
    check('Line_Test / Var_Reset_Set / Hitbox_Hold handlers kept', [fetch(pm, i) for i in (1096, 2000, 2100)],
          [fetch(om, i) for i in (1096, 2000, 2100)])
    check('Effect_Camera handler', fetch(pm, CF.CF_INDEX), lab['h_camfx'])

    # ---- the game's math the cave calls: nop the paired-single saves unicorn can't run
    for lo, n in ((0x033496A0, 0x200), (CF.LOOKAT_INV, 0x60), (CF.ROT, 0x100), (CF.TANF, 0x80), (0x04ADEAB8, 0x40),
                  (0x04ADF434, 0x80), (0x04ADEB48, 0x80), (0x04AE1000, 0x400), (0x0334E0C8, 0x400),
                  (0x03373478, 0x100), (0x033726E8, 0x100)):
        for at in range(lo, lo + 4 * n, 4):
            if r32(pm, at) >> 26 == 4:
                w32(pm, at, 0x60000000)

    # ---- the fake world: effect manager, camera table, an object with the game's EffectModule vtable
    ensure(pm, CF.CAMTBL, CF.CAMTBL + 0x200)
    ensure(pm, CF.MGR, CF.MGR + 4)
    ensure(pm, 0x10439078, 0x1043907C)
    pm.mem_map(MGR_FAKE, 0x10000)
    w32(pm, CF.MGR, MGR_FAKE)
    pool = lambda i: MGR_FAKE + CF.POOL + CF.INST * i       # noqa: E731
    w32(pm, CF.CAMTBL + 0xC, 0)
    w32(pm, CF.CAMTBL + 0x14, SRC)

    def camera(eye, target, up=(0, 1, 0), fov=0.7155849933624268, near=2.0):
        wf(pm, SRC, [fov, 16 / 9, near, 100000.0] + list(eye) + list(target) + list(up))
        return dict(eye=eye, target=target, up=up, fov=fov, near=near)
    cam = camera((30.0, 45.0, 160.0), (5.0, 20.0, 0.0))
    w32(pm, ACC + 0xA0, EM)
    w32(pm, EM, CF.EM_VTABLES[0])
    # the request stub (in place of vt +0x44's first word): records its arguments, makes the instance, returns it
    st = Asm(STUB)
    st.asm("""
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        stw r4, 0(r12)
        lwz r0, 0(r5)
        stw r0, 4(r12)
        lwz r0, 4(r5)
        stw r0, 8(r12)
        lwz r0, 8(r5)
        stw r0, 0xC(r12)
        lwz r0, 0(r6)
        stw r0, 0x10(r12)
        lwz r0, 4(r6)
        stw r0, 0x14(r12)
        lwz r0, 8(r6)
        stw r0, 0x18(r12)
        stw r7, 0x1C(r12)
        stw r8, 0x20(r12)
        stw r9, 0x24(r12)
        stw r10, 0x28(r12)
        stfs f1, 0x2C(r12)
        lwz r11, 0x30(r12)
        stw r11, 0x14(r3)
        lwz r10, 0x34(r12)
        cmpwi r10, 0
        beq st_ret
        stw r11, 0(r10)
st_ret:
        lwz r9, 0x38(r12)
        addi r9, r9, 1
        stw r9, 0x38(r12)
        mr r3, r11
        blr
kill:
        lis r12, 0x%04X
        ori r12, r12, 0x%04X
        lwz r9, 0(r12)
        addi r9, r9, 1
        stw r9, 0(r12)
        slwi r11, r9, 3
        add r11, r11, r12
        stw r3, 0(r11)
        stw r4, 4(r11)
        blr
""" % (REC >> 16, REC & 0xFFFF, KREC >> 16, KREC & 0xFFFF))
    for i, w in enumerate(st.words()):
        w32(pm, STUB + 4 * i, w)
    w32(pm, CF.WORLD_REQ, LT.branch(CF.WORLD_REQ, STUB))
    w32(pm, CF.KILL, LT.branch(CF.KILL, st.addr('kill')))
    pm.mem_write(KREC, b'\0' * 0x100)

    def entry_of(h):
        for k in range(CF.NTAB):
            e = lab['cf_tab'] + CF.ENTRY * k
            if r32(pm, e) == h:
                return e
        return None

    serial = [0x40]

    def camfx(graphic, x, y, z, rx, ry, rz, size, mode, frames=0, flags=0, execute=1, give=None, slot=None):
        """run Effect_Camera's handler; the stub gives handle (slot << 24 | serial) and an instance in pool slot"""
        serial[0] += 1
        if slot is None:
            slot = serial[0] % 90
        h = (slot << 24) | serial[0] if give is None else give
        pm.mem_write(REC, b'\0' * 0x38)
        w32(pm, REC + 0x30, h)
        w32(pm, REC + 0x34, pool(slot) if h else 0)
        pm.mem_write(pool(slot), b'\0' * CF.INST)
        w32(pm, STATE + 4, 0x1000)
        w32(pm, STATE + 8, 0xFFFFFFFF)
        pm.mem_write(FLAG + 8, bytes([execute]))
        pm.mem_write(PARAMS, struct.pack('>Ifffffffiii', graphic, x, y, z, rx, ry, rz, size, mode, frames, flags))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x1000 + r)
        run(pm, lab['h_camfx'], RET, {UC_PPC_REG_3: ACC, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG, UC_PPC_REG_7: PARAMS})
        kept = [r for r in range(14, 32) if pm.reg_read(REG(r)) != 0x1000 + r]
        return dict(ret=pm.reg_read(UC_PPC_REG_3), step=r32(pm, STATE + 4) - 0x1000, kept=kept, h=h, slot=slot,
                    inst=pool(slot), calls=r32(pm, REC + 0x38))

    def ref(c, mode, x, y, z, rot, size):
        return CF.matrix(c['eye'], c['target'], c['up'], c['fov'], c['near'], mode, x, y, z, rot, size)

    def inst_matrix(inst):
        v = rf(pm, inst + 0x50, 12)
        return [v[0:4], v[4:8], v[8:12]]

    # ---- the handler
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0)
    check('Effect_Camera: returns 2, steps 12 words, callee-saved kept', (r['ret'], r['step'], r['kept']), (2, 48, []))
    want = ref(cam, 0, 0, 0, 20, (0, 0, 0), 1)
    check('Mode 0 at (0, 0, 20): the instance\'s matrix = the camera\'s axes, 20 in front of the eye',
          close(inst_matrix(r['inst']), want), True)
    rec = rf(pm, REC + 4, 6)
    check('... the request: the effect id, its place (the matrix\'s translation), rotation 0',
          (r32(pm, REC), close(rec[:3], [want[0][3], want[1][3], want[2][3]]), rec[3:]), (0x1000013, True, [0, 0, 0]))
    check('... flags 0, mta -1, 1, 0, size 1', [r32(pm, REC + o) for o in (0x1C, 0x20, 0x24, 0x28)] +
          [round(rf(pm, REC + 0x2C, 1)[0], 4)], [0, 0xFFFFFFFF, 1, 0, 1.0])
    check('... instance flags: 0x8000 (keep +0x50)', r32(pm, r['inst'] + 0x144), 0x8000)
    e = entry_of(r['h'])
    check('... tracked (handle, mode, frames, flags)', e is not None and [r32(pm, e + o) for o in (4, 8, 0xC)],
          [0, 0, 0])
    eye, tgt = cam['eye'], cam['target']
    fwd = [tgt[i] - eye[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in fwd))
    p = [want[i][3] for i in range(3)]
    check('... 20 units along the view direction from the eye',
          close(p, [eye[i] + fwd[i] / n * 20 for i in range(3)]), True)
    # Mode 0 with offsets and a turn
    r = camfx(0x3410005, 3.0, -2.0, 15.0, 10.0, 20.0, 30.0, 1.5, 0)
    check('Mode 0, offset (3, -2, 15), turn (10, 20, 30), size 1.5', close(inst_matrix(r['inst']),
          ref(cam, 0, 3, -2, 15, (10, 20, 30), 1.5)), True)
    # Mode 1: screen units
    r = camfx(0x1000013, 0.5, -0.25, 30.0, 0.0, 0.0, 90.0, 2.0, 1)
    m1 = ref(cam, 1, 0.5, -0.25, 30, (0, 0, 90), 2.0)
    check('Mode 1, (0.5, -0.25) half screen heights at 30, size 2', close(inst_matrix(r['inst']), m1), True)
    k = 30 * math.tan(cam['fov'] / 2)
    check('... its scale: size x distance x tan(fov / 2) (%.3f)' % (2 * k),
          abs(math.sqrt(sum(m1[i][0] ** 2 for i in range(3))) - 2 * k) < 1e-3 and
          abs(rf(pm, REC + 0x2C, 1)[0] - 2 * k) < 1e-3, True)
    r = camfx(0x1000013, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1)
    check('Mode 1, Z 0: at 20', close(inst_matrix(r['inst']), ref(cam, 1, 0, 0, 20, (0, 0, 0), 1)), True)
    r = camfx(0x1000013, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0)
    check('Mode 0, Z 1 (inside the near clip 2): at near + 1 = 3',
          close(inst_matrix(r['inst']), ref(cam, 0, 0, 0, 3, (0, 0, 0), 1)), True)
    r = camfx(0x1000013, 1.0, 2.0, 25.0, 0.0, 45.0, 0.0, 1.0, 2)
    m2 = inst_matrix(r['inst'])
    check('Mode 2: the camera\'s place, the world\'s turn (45 degrees about the world\'s Y)',
          close(m2, ref(cam, 2, 1, 2, 25, (0, 45, 0), 1)) and close([m2[1][1], m2[0][0]], [1, math.cos(math.pi / 4)]),
          True)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 7)
    check('Mode 7: as 0', close(inst_matrix(r['inst']), ref(cam, 0, 0, 0, 20, (0, 0, 0), 1)) and
          r32(pm, entry_of(r['h']) + 4) == 0, True)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, flags=1)
    check('Flags 1 (unslowed): the request\'s rate-1 flag 0x00800000, the instance\'s 0x01008000',
          (r32(pm, REC + 0x1C), r32(pm, r['inst'] + 0x144)), (0x00800000, 0x01008000))
    calls = r32(pm, REC + 0x38)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, execute=0)
    check('not executing: no request, nothing tracked, still stepped', (r['calls'], entry_of(r['h']), r['step']),
          (calls, None, 48))
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, give=0)
    check('the request refused (no handle): nothing tracked', (r['calls'], entry_of(0) is not None), (calls + 1, True))
    w32(pm, ACC + 0xA0, 0)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0)
    check('no EffectModule: nothing (no crash), stepped', (r['calls'], entry_of(r['h']), r['step']),
          (calls + 1, None, 48))
    w32(pm, ACC + 0xA0, EM)
    w32(pm, EM, CF.EM_VTABLES[0] + 8)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0)
    check('a module whose vt +0x44 isn\'t the world request: nothing', (r['calls'], entry_of(r['h'])), (calls + 1, None))
    w32(pm, EM, CF.EM_VTABLES[1])
    w32(pm, CF.CAMTBL + 0xC, 0xFFFFFFFF)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0)
    check('no camera (the table has no source): nothing started', (r['calls'], entry_of(r['h'])), (calls + 1, None))
    w32(pm, CF.CAMTBL + 0xC, 0)
    r = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0)
    check('the fighter EffectModule class (vtable 0x101228F8): started', (r['calls'], entry_of(r['h']) is not None),
          (calls + 2, True))

    # ---- the calc pass: clear the table, start a known set
    pm.mem_write(lab['cf_tab'], b'\0' * CF.NTAB * CF.ENTRY)
    pm.mem_write(KREC, b'\0' * 0x100)
    a0 = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, slot=10)
    a1 = camfx(0x1000013, 0.5, 0.25, 30.0, 0.0, 0.0, 0.0, 2.0, 1, slot=11)
    a2 = camfx(0x1000013, 1.0, 2.0, 25.0, 0.0, 45.0, 0.0, 1.0, 2, slot=12)
    a3 = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, frames=2, slot=13)
    a4 = camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, slot=14)

    def calc():
        for rr in range(14, 32):
            pm.reg_write(REG(rr), 0x2000 + rr)
        pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
        pm.reg_write(UC_PPC_REG_3, 0x5555AAA0)
        pm.reg_write(UC_PPC_REG_LR, 0x0123ABC0)
        pm.emu_start(CF.CALC_AT, CF.CALC_AT + 4, count=400000)
        ok = all(pm.reg_read(REG(rr)) == 0x2000 + rr for rr in range(14, 32))
        return (ok, pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_1), pm.reg_read(UC_PPC_REG_LR),
                r32(pm, 0x7F00F000 - 0x28) == 0x7F00F000)
    cam = camera((-40.0, 60.0, 120.0), (0.0, 15.0, 0.0), up=(0.1, 1.0, 0.0), fov=0.5)
    check('calc hook: back at 0x032EFD08 with the pass\'s stwu done, r3 / LR / callee-saved kept', calc(),
          (True, 0x5555AAA0, 0x7F00F000 - 0x28, 0x0123ABC0, True))
    check('the camera moved (eye, target, a tilted up, FOV 0.5): Mode 0 follows',
          close(inst_matrix(a0['inst']), ref(cam, 0, 0, 0, 20, (0, 0, 0), 1)), True)
    check('... Mode 1 follows and keeps its screen size (the new FOV)',
          close(inst_matrix(a1['inst']), ref(cam, 1, 0.5, 0.25, 30, (0, 0, 0), 2)), True)
    check('... Mode 2 follows, its turn the world\'s',
          close(inst_matrix(a2['inst']), ref(cam, 2, 1, 2, 25, (0, 45, 0), 1)), True)
    s1 = math.sqrt(sum(inst_matrix(a1['inst'])[i][0] ** 2 for i in range(3)))
    cam = camera((-40.0, 60.0, 120.0), (0.0, 15.0, 0.0), up=(0.1, 1.0, 0.0), fov=0.25)
    calc()
    s2 = math.sqrt(sum(inst_matrix(a1['inst'])[i][0] ** 2 for i in range(3)))
    check('zoomed in (FOV 0.5 -> 0.25): Mode 1\'s scale follows tan(fov / 2) (%.3f -> %.3f)' % (s1, s2),
          abs(s2 / s1 - math.tan(0.125) / math.tan(0.25)) < 1e-4, True)
    s0 = math.sqrt(sum(inst_matrix(a0['inst'])[i][0] ** 2 for i in range(3)))
    check('... Mode 0\'s scale doesn\'t (1)', abs(s0 - 1) < 1e-4, True)
    check('Frames 2: faded out after its 2nd frame (the kill facade with its handle, 0)',
          (r32(pm, KREC), r32(pm, KREC + 8), r32(pm, KREC + 12)), (1, a3['h'], 0))
    check('... still attached while it fades (tracked, Frames 0 now)', (entry_of(a3['h']) is not None,
          r32(pm, entry_of(a3['h']) + 8)), (True, 0))
    w32(pm, a3['inst'], 0)                        # its fade is over: the instance is free
    w32(pm, a4['inst'], 0x0E000999)               # a4's slot reused by another effect
    before = inst_matrix(a4['inst'])
    cam = camera((0.0, 0.0, 200.0), (0.0, 0.0, 0.0))
    calc()
    check('an ended effect / a reused slot: dropped, the new effect\'s matrix untouched',
          (entry_of(a3['h']), entry_of(a4['h']), close(inst_matrix(a4['inst']), before)), (None, None, True))
    check('... the others go on (Mode 0 at the new camera)',
          close(inst_matrix(a0['inst']), ref(cam, 0, 0, 0, 20, (0, 0, 0), 1)), True)
    check('... no second kill', r32(pm, KREC), 1)
    w32(pm, CF.CAMTBL + 0xC, 0xFFFFFFFF)
    before = inst_matrix(a0['inst'])
    camera((100.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    calc()
    check('no camera this frame: left where it was (still tracked)',
          (close(inst_matrix(a0['inst']), before), entry_of(a0['h']) is not None), (True, True))
    w32(pm, CF.CAMTBL + 0xC, 0)
    w32(pm, a0['inst'] + 0x144, 0)
    calc()
    check('its flag 0x8000 set again each frame', r32(pm, a0['inst'] + 0x144), 0x8000)
    # the 17th effect: the oldest is faded out
    pm.mem_write(lab['cf_tab'], b'\0' * CF.NTAB * CF.ENTRY)
    w32(pm, lab['cf_rr'], 0)
    pm.mem_write(KREC, b'\0' * 0x100)
    hs = [camfx(0x1000013, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0, slot=20 + i)['h'] for i in range(17)]
    check('16 tracked at once; the 17th fades the first out and takes its entry',
          (r32(pm, KREC), r32(pm, KREC + 8), entry_of(hs[0]), entry_of(hs[16]) is not None,
           all(entry_of(h) is not None for h in hs[1:])), (1, hs[0], None, True, True))

    # ---- the game's instance update (0x0334E0C8) up to its matrix for eft (sp + 0x10, before the follow test)
    def game_update(flags):
        inst = pool(50)
        pm.mem_write(inst, b'\0' * CF.INST)
        w32(pm, inst, 0x32000001)
        wf(pm, inst + 0x50, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])          # what the cave would have written
        wf(pm, inst + 0xB0, [2, 2, 2])                                          # scale, rotation 0, position (5, 6, 7)
        wf(pm, inst + 0xC8, [5, 6, 7])
        wf(pm, inst + 0x138, [1, 1, 0])
        w32(pm, inst + 0x144, flags)
        wf(pm, 0x10439078, [1])
        pm.reg_write(UC_PPC_REG_LR, RET)
        pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
        pm.reg_write(UC_PPC_REG_3, inst)
        try:
            pm.emu_start(0x0334E0C8, 0x0334E2C0, count=200000)
        except UcError as ex:
            return 'error %s at 0x%08X' % (ex, pm.reg_read(UC_PPC_REG_PC)), None
        sp = pm.reg_read(UC_PPC_REG_1)
        return rf(pm, inst + 0x50, 12), rf(pm, sp + 0x10, 12)
    m, stack = game_update(0x8000)
    check('game update, flag 0x8000: +0x50 kept as written, and it is the matrix the update goes on with',
          (m, stack), ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]))
    m, stack = game_update(0)
    check('game update, no flag: +0x50 rebuilt from its scale / rotation / position (2, 0, (5, 6, 7))',
          (m, stack), ([2, 0, 0, 5, 0, 2, 0, 6, 0, 0, 2, 7], [2, 0, 0, 5, 0, 2, 0, 6, 0, 0, 2, 7]))
    dbg = [r32(pm, lab['cf_dbg'] + 4 * i) for i in range(6)]
    check('debug counters: commands run, started, matrices set, ended by Frames, ended, refused',
          (dbg[0] > 20, dbg[1] > 20, dbg[2] > 5, dbg[3], dbg[4], dbg[5]), (True, True, True, 1, 2, 4))
    sys.exit(1 if acmd_ext_test.fails else 0)


if __name__ == '__main__':
    main()
