#!/usr/bin/env python3
"""Unicorn test of tools/line_test_cave.py on an executable with acmd_ext_cave.py's patches (exe_v46v_threads):

  python3 tools/line_test_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). The game's ray check (0x02C39FB4) and
PostureModuleF wrapper are stubbed: a stage of one wall at world x = WX (normal pointing at the caller) and one floor
at y = FY; the object at (PX, PY) facing LR. Checked: the command tables (the game's search, both loaders, the
handler fetch) for Line_Test and for vanilla / acmd_ext commands; Line_Test's results in its variables (relative and
world space, a wall, a floor, nothing met, the platforms flag passed to the ray check, the script stepped over); the
LINE_* variables through the game's WorkModule get / set_float (callee-saved registers kept, per object, other IDs
untouched).
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import kind_expand as K  # noqa: E402
import line_test_cave as L  # noqa: E402
from acmd_ext_test import check, r32, w32, run, fcall, RET, CRC_TABLE, COUNT, SIZES, HANDLERS, BUF  # noqa: E402
import acmd_ext_test  # noqa: E402
from ppcasm import Asm  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6, UC_PPC_REG_7,  # noqa: E402
                               UC_PPC_REG_28, UC_PPC_REG_29, UC_PPC_REG_30, UC_PPC_REG_0, UC_PPC_REG_12)

FGET, FSET = 0x02F1DBE4, 0x02F1DC04
WX, FY = -100.0, -20.0
STUB = 0x7E000000


def stubs(pm, px, py, lr):
    pm.mem_map(STUB, 0x10000)
    a = Asm(STUB)
    a.asm("""
posture:                        # PostureModuleF wrapper(ctx, {args, n}): op 0 lr, 1 x, 2 y (floats at +0x1F00)
        lwz r9, 0(r4)
        lwz r9, 0(r9)
        slwi r9, r9, 2
        lis r11, 0x7E00
        addi r11, r11, 0x1F00
        lwzx r3, r11, r9
        blr
ray:                            # (GM, from, dir, out, normal, all): the wall x = WX, then the floor y = FY
        lis r11, 0x7E00
        stw r8, 0x1F40(r11)             # log `all`
        lfs f0, 0x1F20(r11)             # WX
        lfs f1, 0(r4)
        lfs f2, 4(r4)
        lfs f3, 0(r5)
        lfs f4, 4(r5)
        lfs f9, 0x1F28(r11)             # 0
        fcmpu cr0, f3, f9
        beq ray_floor
        fsubs f5, f0, f1
        fdivs f5, f5, f3                # t
        fcmpu cr0, f5, f9
        blt ray_floor
        lfs f10, 0x1F2C(r11)            # 1
        fcmpu cr0, f5, f10
        bgt ray_floor
        stfs f0, 0(r6)
        fmadds f6, f5, f4, f2
        stfs f6, 4(r6)
        lfs f7, 0x1F2C(r11)
        fcmpu cr0, f3, f9
        blt ray_nx
        fneg f7, f7
ray_nx:
        stfs f7, 0(r7)
        stfs f9, 4(r7)
        li r3, 1
        blr
ray_floor:
        lfs f0, 0x1F24(r11)             # FY
        fcmpu cr0, f4, f9
        beq ray_none
        fsubs f5, f0, f2
        fdivs f5, f5, f4
        fcmpu cr0, f5, f9
        blt ray_none
        lfs f10, 0x1F2C(r11)
        fcmpu cr0, f5, f10
        bgt ray_none
        fmadds f6, f5, f3, f1
        stfs f6, 0(r6)
        stfs f0, 4(r6)
        stfs f9, 0(r7)
        stfs f10, 4(r7)
        li r3, 1
        blr
ray_none:
        li r3, 0
        blr
setf:                           # a WorkModule vt +0x4C(wm, id, f1): log {id, f1} at +0x2000
        lis r11, 0x7E00
        lwz r12, 0x1FF0(r11)
        stw r4, 0(r12)
        stfs f1, 4(r12)
        addi r12, r12, 8
        stw r12, 0x1FF0(r11)
        blr
""")
    for i, w in enumerate(a.words()):
        w32(pm, STUB + 4 * i, w)
    pm.mem_write(STUB + 0x1F00, struct.pack('>fff', lr, px, py))
    pm.mem_write(STUB + 0x1F20, struct.pack('>ffff', WX, FY, 0.0, 1.0))
    for wrap, to in ((L.POSTURE_FW, a.addr('posture')), (L.RAY_N, a.addr('ray'))):
        for i, wd in enumerate([0x3D800000 | (to >> 16), 0x618C0000 | (to & 0xFFFF), 0x7D8903A6, 0x4E800420]):
            w32(pm, wrap + 4 * i, wd)
    return a


def f32(pm, at):
    return round(struct.unpack('>f', pm.mem_read(at, 4))[0], 3)


def main():
    exe = sys.argv[1]
    img = K.Image(exe)
    words, lab, s = L.build(img.w)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    lt = zlib.crc32(b'Line_Test') & 0xFFFFFFFF
    pairs = [(r32(om, CRC_TABLE + 8 * i), r32(om, CRC_TABLE + 8 * i + 4)) for i in range(COUNT)]
    check('Line_Test CRC not in the game table', lt in dict(pairs), False)
    check('Line_Test CRC not an acmd_ext command', lt in [C.crc(c[0]) for c in C.COMMANDS], False)

    def lookup(mu, crc):
        run(mu, 0x02BEE154, RET, {UC_PPC_REG_3: crc})
        return mu.reg_read(UC_PPC_REG_3)
    check('vanilla CRCs keep their index', [hex(c) for c, i in pairs[::37] if lookup(pm, c) != i], [])
    check('acmd_ext CRCs keep theirs', [lookup(pm, C.crc(c[0])) for c in C.COMMANDS],
          [C.NEW_BASE + k for k in range(len(C.COMMANDS))])
    check('Line_Test -> its index', lookup(pm, lt), L.LT_BASE)
    check('unknown CRC -> -1', lookup(pm, 0x12345678), 0xFFFFFFFF)

    # both loaders over: Hitbox, Line_Test, FRAME, Joint_Position_Get
    idx = dict(pairs)
    size = {i: r32(om, SIZES + 4 * i) for _, i in pairs}
    jp = [c for c in C.COMMANDS if c[0] == 'Joint_Position_Get'][0]
    script = [0xB738EABD, lt, 0x42ACFE7D, C.crc(jp[0])]
    want_idx = [idx[0xB738EABD], L.LT_BASE, idx[0x42ACFE7D], C.NEW_BASE + C.COMMANDS.index(jp)]
    want_size = [size[want_idx[0]], 11, size[want_idx[2]], jp[1]]
    for loop, (start, stop, regs) in enumerate([
            (0x02BEE2B4, 0x02BEE2D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_29: 0, UC_PPC_REG_30: len(script),
                                      UC_PPC_REG_4: SIZES}),
            (0x02BEE3B4, 0x02BEE3D8, {UC_PPC_REG_28: BUF, UC_PPC_REG_4: 0, UC_PPC_REG_29: len(script),
                                      UC_PPC_REG_30: SIZES})]):
        pm.mem_write(BUF, b'\0' * 0x1000)
        o, offs = 0, []
        for c, sz in zip(script, want_size):
            w32(pm, BUF + 4 * o, c)
            offs.append(o)
            o += sz
        run(pm, start, stop, regs)
        check('loader %d: indices' % (loop + 1), [r32(pm, BUF + 4 * x) for x in offs], want_idx)
        check('loader %d: words stepped' % (loop + 1), pm.reg_read(UC_PPC_REG_29 if loop == 0 else UC_PPC_REG_4),
              sum(want_size))

    def fetch(mu, i):
        run(mu, 0x02BEE84C, 0x02BEE854, {UC_PPC_REG_7: i, UC_PPC_REG_29: HANDLERS, UC_PPC_REG_12: 0x55})
        return mu.reg_read(UC_PPC_REG_0)
    check('vanilla handlers unchanged', [i for _, i in pairs[::23] if fetch(pm, i) != r32(om, HANDLERS + 4 * i)], [])
    check('acmd_ext handler kept', fetch(pm, want_idx[3]), fetch(om, want_idx[3]))
    check('Line_Test handler', fetch(pm, L.LT_BASE), lab['h_line'])

    # the object: facing left at (20, 5)
    px, py, lr = 20.0, 5.0, -1.0
    st = stubs(pm, px, py, lr)
    acc, wm, wmvt, gm = 0x10380000, 0x10380200, 0x10380300, 0x10380400
    w32(pm, acc + 0x28, wm)
    w32(pm, acc + 0x2C, gm)
    w32(pm, wm, wmvt)
    w32(pm, wmvt + 0x4C, st.addr('setf'))
    state, flag, params = 0x10373000, 0x10374000, 0x10375000

    def line(space, x0, y0, x1, y1, floors, vs=(0x0F000300, 0x0F000301, 0x0F000302, 0x0F000303)):
        w32(pm, STUB + 0x1FF0, STUB + 0x2000)
        w32(pm, state + 4, 0x1000)
        w32(pm, state + 8, 0xFFFFFFFF)
        pm.mem_write(flag + 8, b'\1')
        pm.mem_write(params, struct.pack('>iffffi4I', space, x0, y0, x1, y1, floors, *vs))
        run(pm, lab['h_line'], RET, {UC_PPC_REG_3: acc, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
        n = (r32(pm, STUB + 0x1FF0) - STUB - 0x2000) // 8
        log = {r32(pm, STUB + 0x2000 + 8 * i): f32(pm, STUB + 0x2004 + 8 * i) for i in range(n)}
        return pm.reg_read(UC_PPC_REG_3), r32(pm, state + 4) - 0x1000, r32(pm, STUB + 0x1F40), log
    V = lambda i: 0x0F000300 + i                          # noqa: E731
    # relative, forward 8 -> 300 at height 10: facing left, the wall x = -100 is 120 ahead
    r3, step, allf, log = line(0, 8.0, 10.0, 300.0, 10.0, 1)
    check('Line_Test returns 2, steps 11 words', (r3, step), (2, 44))
    check('Floors 1 -> ray_check all 0', allf, 0)
    check('wall ahead: distance / hit X / Y / kind', [log.get(V(i)) for i in range(4)], [112.0, 120.0, 10.0, 2.0])
    r3, step, allf, log = line(0, 8.0, 10.0, 60.0, 10.0, 0)
    check('nothing within reach: whole length, the end, kind 0; all 1', ([log.get(V(i)) for i in range(4)], allf),
          ([52.0, 60.0, 10.0, 0.0], 1))
    r3, step, allf, log = line(0, 0.0, 10.0, 0.0, -100.0, 0)
    check('straight down: the floor y = -20 (25 below him)', [log.get(V(i)) for i in range(4)], [35.0, 0.0, -25.0, 1.0])
    r3, step, allf, log = line(1, 0.0, 0.0, -200.0, 0.0, 0)
    check('world space: the wall at x = -100', [log.get(V(i)) for i in range(4)], [100.0, -100.0, 0.0, 2.0])
    r3, step, allf, log = line(0, 8.0, 10.0, 300.0, 10.0, 1, vs=(0, V(7), 0, 0))
    check('variables 0 not stored', log, {V(7): 120.0})
    pm.mem_write(flag + 8, b'\0')
    w32(pm, STUB + 0x1FF0, STUB + 0x2000)
    w32(pm, state + 8, 0)
    run(pm, lab['h_line'], RET, {UC_PPC_REG_3: acc, UC_PPC_REG_5: state, UC_PPC_REG_6: flag, UC_PPC_REG_7: params})
    check('not executing: nothing stored', r32(pm, STUB + 0x1FF0), STUB + 0x2000)

    # the variables, through the game's WorkModule float get / set (the object's accessor from acmd_ext's cache:
    # its per-frame hook)
    mm = 0x10383000
    w32(pm, mm + 4, acc)
    run(pm, C.FRAME_HOOK, C.FRAME_HOOK + 4, {UC_PPC_REG_3 + 28: mm})
    X = lambda i: 0x0F000000 + L.VAR_LO + i               # noqa: E731
    check('no entry yet: LINE_TEST reads 0', fcall(pm, FGET, wm, X(4)), 0.0)
    for i, v in enumerate((8.0, 10.0, 300.0, 10.0)):
        fcall(pm, FSET, wm, X(i), v)
    check('inputs read back', [fcall(pm, FGET, wm, X(i)) for i in range(4)], [8.0, 10.0, 300.0, 10.0])
    fcall(pm, FSET, wm, X(4), 2.0)                       # Space 0, Floors 1
    check('LINE_TEST / DIST / HIT_X / HIT_Y / KIND / NX / NY', [fcall(pm, FGET, wm, X(i)) for i in range(4, 11)],
          [1.0, 112.0, 120.0, 10.0, 2.0, -1.0, 0.0])   # the normal points back at him
    check('mode passed: all 0', r32(pm, STUB + 0x1F40), 0)
    check('results are read only', (fcall(pm, FSET, wm, X(6), 5.0), fcall(pm, FGET, wm, X(6))), (5.0, 120.0))
    check('another object: nothing', fcall(pm, FGET, 0x10390200, X(5)), 0.0)
    check('0x3DB: still 0', fcall(pm, FGET, wm, X(11)), 0.0)
    check('user VAR_5 untouched', (fcall(pm, FSET, wm, V(5), 3.0), fcall(pm, FGET, wm, V(5))), (3.0, 3.0))
    sys.exit(1 if acmd_ext_test.fails else 0)


if __name__ == '__main__':
    main()
