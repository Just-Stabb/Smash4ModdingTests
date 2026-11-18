#!/usr/bin/env python3
"""Test of tools/mesh_vis_cave.py (Mesh_Visibility) on an executable with tools/outline_cave.py's patches
(exe_v46z_ol):

  python3 tools/mesh_vis_test.py EXE.rpx

The cave's words are written into the emulated image (the file isn't patched). Run with the game's own code around
the hooks (unicorn), on a fake model instance laid out as the game's code reads it (the per-mesh bytes [[MI + 0x7DC] +
4], the model data [MI + 0x6E4] with its mesh count +0x44 and resource (vt +0xA4 a mesh, the mesh's vt +0x2C its name:
small stubs), the result array the instance's vt +0x74 writes, its change listener [MI + 0x7EC]: a stub):
  - the command tables for Mesh_Visibility and every earlier cave's command (Outline_Set included);
  - the handler: by name (CRC32: the same mesh the game's own by-name setter 0x0342633C finds), by index, Visible 0 / 1
    / 2, Persist, Mesh -1, an unknown name, an object without a model;
  - the game's setter 0x034232FC (hooked): a visibility-group write (which 0) to an overridden mesh kept aside and put
    back when the override ends, the animation's bit (which 1) and other meshes as before;
  - what is drawn: the instance's vt +0x74 (0x03424E88, the game's) run on the bytes: an overridden mesh hidden / shown
    whatever the animation's bit says;
  - the tick (0x032EFB78 -> mv_tick -> outline's ol_tick -> screen_invert's si_tick): Persist 0 ends when the motion
    kind changes, Persist 1 stays, a KO ends it, a changed model drops it;
  - the clear chain (0x02FB3498 -> ... -> ol_clear -> mv_clear -> 0x02FB349C): every override ends, bytes put back;
  - v2: a mesh with two parts (polygons) whose second entry has no name of its own (or the same name): both parts
    hidden / shown / given back, the next named mesh left alone;
  - the diag build's lines.
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mesh_vis_cave as MV  # noqa: E402
import outline_cave as OL  # noqa: E402
import line_test_cave as LT  # noqa: E402
import acmd_ext_test  # noqa: E402
from acmd_ext_test import check, r32, w32, run, RET  # noqa: E402
from outline_test import table_tests, ensure, EARLIER, SMGR  # noqa: E402
from stage_slot_test import machine  # noqa: E402
from ppcasm import Asm  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_0, UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5,  # noqa: E402
                               UC_PPC_REG_6, UC_PPC_REG_7, UC_PPC_REG_10, UC_PPC_REG_LR, UC_PPC_REG_MSR,
                               UC_PPC_REG_PC)

REG = lambda n: UC_PPC_REG_0 + n          # noqa: E731
PARAMS, STATE, FLAG = 0x7F001400, 0x7F001600, 0x7F001700
W0 = 0x7F040000                           # the fake world (0x10000)
STUBS = 0x04BE5800                        # code stubs past the cave
NAMES = ['stethoscope_VIS_O_OBJ', 'MarioD_hair_O_OBJ', 'Mario_Eye_VIS_O_OBJ', 'Mario_Result_VIS_O_OBJ', 'Gamemodel']
ALL = dict(EARLIER, Outline_Set=2400)


class Model:
    """an object (accessor) with a model instance of len(NAMES) meshes"""

    def __init__(self, mu, k, stubs):
        self.mu, b = mu, W0 + 0x2000 * k
        self.acc, self.mm, self.mi, self.sm, self.mo = b, b + 0x100, b + 0x200, b + 0xB00, b + 0xC00
        self.vis, self.bytes, self.md, self.res = b + 0xA00, b + 0xA20, b + 0xA40, b + 0x1000
        self.outp, self.out, self.meshes, self.names = b + 0x1020, b + 0x1040, b + 0xD00, b + 0xE00
        self.lst, self.lis = b + 0x1800, b + 0x1060
        mu.mem_write(b, b'\0' * 0x2000)
        w32(mu, self.acc + 0x3C, self.mm)
        w32(mu, self.mm + 0xC, self.mi)
        w32(mu, self.acc + 0x20, self.sm)
        w32(mu, self.sm, OL.FIGHTER_SM_VT)
        w32(mu, self.acc + MV.MOTION_ACC, self.mo)
        w32(mu, self.mo + MV.MOTION_KIND, 0x1A0)
        w32(mu, self.mi + MV.VIS_ARR, self.vis)
        w32(mu, self.vis, len(NAMES))
        w32(mu, self.vis + 4, self.bytes)
        w32(mu, self.mi + MV.MDATA, self.md)
        w32(mu, self.md, self.res)
        w32(mu, self.md + 4, self.outp)
        w32(mu, self.outp + 8, self.out)
        w32(mu, self.md + 0x3C, 0)
        w32(mu, self.md + 0x44, len(NAMES))
        w32(mu, self.res, stubs['res_vt'])
        w32(mu, self.res + 4, self.meshes)
        w32(mu, self.mi + 0x7EC, self.lis)
        w32(mu, self.lis, stubs['lis_vt'])
        w32(mu, self.mi + 0x7F0, self.lst)
        for i, n in enumerate(NAMES):
            m = self.meshes + 0x10 * i
            w32(mu, m, stubs['mesh_vt'])
            w32(mu, m + 4, self.names + 0x40 * i)
            mu.mem_write(self.names + 0x40 * i, n.encode() + b'\0')
        for i in range(len(NAMES)):
            self.set_byte(i, 0x11 if i != 2 else 0x26)     # shown; the eye follows its animation (bit 2 on)

    def byte(self, i):
        return self.mu.mem_read(self.bytes + i, 1)[0]

    def set_byte(self, i, v):
        self.mu.mem_write(self.bytes + i, bytes([v]))


def stubs_src():
    return """
res_a4:                                 # res vt +0xA4(res, i, 0) -> its mesh i
        lwz r3, 4(r3)
        slwi r4, r4, 4
        add r3, r3, r4
        blr
mesh_2c:                                # mesh vt +0x2C -> its name
        lwz r3, 4(r3)
        blr
lis_nop:
        blr
res_vt:
""" + '        .word 0\n' * 0x29 + """        .word res_a4_addr
mesh_vt:
""" + '        .word 0\n' * 0xB + """        .word mesh_2c_addr
lis_vt:
""" + '        .word 0\n' * 7 + """        .word lis_nop_addr
        .word 0
        .word lis_nop_addr
"""


def put_stubs(mu):
    ensure(mu, STUBS, STUBS + 0x400)
    a = Asm(STUBS)
    text = stubs_src()
    a.asm(text.replace('res_a4_addr', '0').replace('mesh_2c_addr', '0').replace('lis_nop_addr', '0'))
    text = text.replace('res_a4_addr', str(a.addr('res_a4'))).replace('mesh_2c_addr', str(a.addr('mesh_2c'))) \
        .replace('lis_nop_addr', str(a.addr('lis_nop')))
    a = Asm(STUBS)
    a.asm(text)
    for i, x in enumerate(a.words()):
        w32(mu, STUBS + 4 * i, x)
    assert r32(mu, a.addr('res_vt') + 0xA4) == a.addr('res_a4')
    assert r32(mu, a.addr('mesh_vt') + 0x2C) == a.addr('mesh_2c')
    assert r32(mu, a.addr('lis_vt') + 0x1C) == a.addr('lis_nop') and r32(mu, a.addr('lis_vt') + 0x24) == \
        a.addr('lis_nop')
    return a.labels


def main():
    exe = sys.argv[1]
    orig = MV.rpx_reader(exe)
    words, lab, s = MV.build(orig)
    om, pm = machine(exe), machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    check('present() on the patched words / the unpatched exe',
          (MV.present(lambda x: words.get(x, orig(x))), MV.present(orig)), (True, False))
    check('... the outline cave present in the exe it builds on', OL.present(orig), True)
    try:
        MV.build(lambda x: words.get(x, orig(x)))
        check('building over itself refused', False, True)
    except AssertionError:
        check('building over itself refused', True, True)
    inside = [a for a in words if MV.CAVE <= a < MV.LIMIT]
    check('the cave inside its region (0x04BE4000-0x04BE5000)', (min(inside), max(inside) < MV.LIMIT),
          (MV.CAVE, True))
    others = sorted(a for a in words if not MV.CAVE <= a < MV.LIMIT)
    check('words outside the cave: the setter, the tick, the clear chain\'s end and the 4 table fallbacks', others,
          sorted([MV.SETVIS, OL.TICK_AT, s['clear_at'], s['lk_none'], s['s1'], s['s2'], s['f']]))
    check('... the setter / clear a b, the tick a bl', [words[MV.SETVIS] & 3, words[OL.TICK_AT] & 3,
                                                        words[s['clear_at']] & 3], [0, 1, 0])
    check('... chained on the outline cave\'s tick, clear and tables (0x04BE3000-0x04BE4000)',
          [OL.CAVE <= x < OL.LIMIT for x in [s['tick_prev'], s['clear_at']] +
           [LT.bdecode(s[k], s[k + '_word']) for k in ('lk_none', 's1', 's2', 'f')]], [True] * 6)
    table_tests(pm, om, s, words, lab, 'mv', MV.CMD_NAME, MV.MV_INDEX, MV.CMD_CRC, 1 + MV.NPARAMS, 'h_meshvis', ALL)

    pm.reg_write(UC_PPC_REG_MSR, pm.reg_read(UC_PPC_REG_MSR) | 0x2000)
    ensure(pm, W0, W0 + 0x10000)
    st = put_stubs(pm)
    m0, m1 = Model(pm, 0, st), Model(pm, 1, st)
    g, tab = lab['mv_g'], lab['mv_tab']

    def mv(model, mesh, visible, persist, target=0, execute=1):
        w32(pm, STATE + 4, 0x1000)
        w32(pm, STATE + 8, 0xFFFFFFFF)
        pm.mem_write(FLAG + 8, bytes([execute]))
        pm.mem_write(PARAMS, struct.pack('>iIii', target, mesh & 0xFFFFFFFF, visible, persist))
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x1000 + r)
        run(pm, lab['h_meshvis'], RET, {UC_PPC_REG_3: model.acc, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                         UC_PPC_REG_7: PARAMS})
        kept = [r for r in range(14, 32) if pm.reg_read(REG(r)) != 0x1000 + r]
        return dict(ret=pm.reg_read(UC_PPC_REG_3), step=r32(pm, STATE + 4) - 0x1000, kept=kept,
                    hits=r32(pm, g + 0x14))

    def entries():
        out = []
        for k in range(MV.N_ENT):
            a = tab + MV.ENT * k
            if r32(pm, a):
                out.append(dict(acc=r32(pm, a), mi=r32(pm, a + 4), i=r32(pm, a + 8), forced=r32(pm, a + 0xC),
                                saved=r32(pm, a + 0x10), per=r32(pm, a + 0x14), kind=r32(pm, a + 0x18)))
        return out

    def setter(model, i, value, which):
        run(pm, MV.SETVIS, RET, {UC_PPC_REG_3: model.mi, UC_PPC_REG_4: i, UC_PPC_REG_5: value, UC_PPC_REG_6: which})
        return pm.reg_read(UC_PPC_REG_3)

    def drawn(model):
        """the instance's vt +0x74 (0x03424E88, the game's): the result array"""
        for r in range(14, 32):
            pm.reg_write(REG(r), 0x3000 + r)
        run(pm, MV.APPLY, RET, {UC_PPC_REG_3: model.mi})
        return list(pm.mem_read(model.out, len(NAMES)))

    def tick(n=1):
        for _ in range(n):
            pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
            pm.reg_write(UC_PPC_REG_3, SMGR)
            pm.reg_write(REG(30), 0x7F00E000)
            pm.reg_write(UC_PPC_REG_LR, RET)
            pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=200000)

    ensure(pm, SMGR, SMGR + 0x1000)
    pm.mem_write(SMGR, b'\0' * 0xE80)
    check('the game\'s own vt +0x74 on the fake model: every mesh drawn (the eye: its animation bit)', drawn(m0),
          [1, 1, 1, 1, 1])
    # the game's own by-name setter finds the same mesh
    run(pm, MV.BYNAME, RET, {UC_PPC_REG_3: m1.mi, UC_PPC_REG_4: m1.names + 0x40 * 4, UC_PPC_REG_5: 0,
                             UC_PPC_REG_6: 0})
    check('the game\'s by-name setter 0x0342633C on the fake model: "Gamemodel" is mesh 4 (bits 0-1 = 0)',
          (pm.reg_read(UC_PPC_REG_3), m1.byte(4) & 3), (1, 0))
    m1.set_byte(4, 0x11)

    r = mv(m0, MV.crc32('stethoscope_VIS_O_OBJ'), 0, 0)
    check('Mesh_Visibility(self, "stethoscope_VIS_O_OBJ", hide, Persist 0): returns 2, steps 5 words, callee-saved kept,'
          ' 1 mesh matched', (r['ret'], r['step'], r['kept'], r['hits']), (2, 20, [], 1))
    e = entries()
    check('... an entry: mesh 0 of the instance, forced 0, the game\'s bits (1) kept, Persist 0, the motion kind',
          [(x['acc'], x['mi'], x['i'], x['forced'], x['saved'], x['per'], x['kind']) for x in e],
          [(m0.acc, m0.mi, 0, 0, 1, 0, 0x1A0)])
    check('... its byte\'s bits 0-1 = 0 (hidden), the rest kept', m0.byte(0), 0x10)
    check('... drawn: mesh 0 hidden, the rest shown', drawn(m0), [0, 1, 1, 1, 1])
    check('... the other object untouched', drawn(m1), [1, 1, 1, 1, 1])
    check('the game\'s group write (which 0) to the hidden mesh: kept aside (r3 1), the mesh stays hidden',
          (setter(m0, 0, 1, 0), m0.byte(0) & 3, e and entries()[0]['saved']), (1, 0, 1))
    setter(m0, 0, 2, 0)
    check('... another (2: follow the animation) kept aside too', entries()[0]['saved'], 2)
    check('the animation\'s bit (which 1) still written (bit 2 on), the mesh still hidden',
          (setter(m0, 0, 1, 1), m0.byte(0) & 7, drawn(m0)[0]), (1, 4, 0))
    check('a group write to another mesh: as before', (setter(m0, 1, 0, 0), m0.byte(1) & 3, drawn(m0)[1]), (1, 0, 0))
    setter(m0, 1, 1, 0)
    tick(3)
    check('ticks with the same motion: still hidden', (len(entries()), drawn(m0)[0]), (1, 0))
    w32(pm, m0.mo + MV.MOTION_KIND, 0x1A1)
    tick(1)
    check('the motion kind changed (Persist 0): the override ends, the game\'s last group write (2) is back, drawn '
          'by the animation bit (on)', (entries(), m0.byte(0) & 7, drawn(m0)[0]), ([], 6, 1))
    w32(pm, m0.mo + MV.MOTION_KIND, 0x1A0)

    # Persist 1, show, Visible 2, index, -1
    m0.set_byte(2, 0x22)                # the eye: follow the animation, its bit off (hidden by the animation)
    check('the eye hidden by its animation (bits 0-1 2, bit 2 off)', drawn(m0)[2], 0)
    r = mv(m0, MV.crc32('Mario_Eye_VIS_O_OBJ'), 1, 1)
    check('Mesh_Visibility(eye, show, Persist 1): shown over the animation', (r['hits'], drawn(m0)[2]), (1, 1))
    w32(pm, m0.mo + MV.MOTION_KIND, 0x1A2)
    tick(2)
    check('... the motion changes: still shown (Persist 1)', (len(entries()), drawn(m0)[2]), (1, 1))
    r = mv(m0, MV.crc32('Mario_Eye_VIS_O_OBJ'), 2, 0)
    check('Visible 2: the override ends, the animation decides again (hidden)', (entries(), m0.byte(2) & 3,
                                                                                 drawn(m0)[2]), ([], 2, 0))
    r = mv(m0, 4, 0, 1)
    check('Mesh 4 (an index): "Gamemodel" hidden', (r['hits'], drawn(m0)[4]), (1, 0))
    r = mv(m0, 4, 0, 0)
    check('... the same mesh again with Persist 0: one entry, updated', [(x['i'], x['per']) for x in entries()],
          [(4, 0)])
    mv(m0, MV.crc32('MarioD_hair_O_OBJ'), 0, 1)
    mv(m1, MV.crc32('MarioD_hair_O_OBJ'), 0, 1)
    r = mv(m0, -1, 0, 0)
    check('Mesh -1: every override of this object ends (bytes back), the other object\'s stays',
          ([x['acc'] for x in entries()], drawn(m0), drawn(m1)), ([m1.acc], [1, 1, 0, 1, 1], [1, 0, 1, 1, 1]))
    r = mv(m0, MV.crc32('no_such_mesh'), 0, 1)
    check('an unknown name: nothing (stepped)', (r['step'], r['hits'], len(entries())), (20, 0, 1))
    r = mv(m0, 9, 0, 1)
    check('an index past the meshes: nothing', (r['hits'], len(entries())), (0, 1))
    r = mv(m0, MV.crc32('Gamemodel'), 0, 1, execute=0)
    check('not executed (execute flag 0): stepped, nothing changed', (r['step'], len(entries())), (20, 1))
    w32(pm, m0.acc + 0x3C, 0)
    r = mv(m0, MV.crc32('Gamemodel'), 0, 1)
    check('an object with no ModelModule: nothing', (r['step'], len(entries())), (20, 1))
    w32(pm, m0.acc + 0x3C, m0.mm)

    # KO, a changed model
    w32(pm, m1.sm + 0x48, OL.DEAD)
    tick(1)
    check('a KO ends the other object\'s override (byte back: shown)', (entries(), drawn(m1)), ([], [1, 1, 1, 1, 1]))
    w32(pm, m1.sm + 0x48, 0)
    mv(m1, MV.crc32('Gamemodel'), 0, 1)
    w32(pm, m1.mm + 0xC, m0.mi)
    tick(1)
    check('the object\'s model changed: dropped (that model left alone)', entries(), [])
    w32(pm, m1.mm + 0xC, m1.mi)
    m1.set_byte(4, 0x11)

    # v2: a mesh with two parts (polygons): the entry after it has no name of its own (or the same name)
    hair = MV.crc32('MarioD_hair_O_OBJ')
    pm.mem_write(m1.names + 0x40 * 2, b'\0')
    b0 = [m1.byte(i) for i in range(len(NAMES))]
    r = mv(m1, hair, 0, 1)
    check('v2: a two-part mesh (the entry after it has no name): both parts hidden, the next named mesh not',
          (r['hits'], sorted(x['i'] for x in entries() if x['acc'] == m1.acc), drawn(m1)), (2, [1, 2], [1, 0, 0, 1, 1]))
    check('... each part\'s byte bits 0-1 = 0, the game\'s bits kept for the end',
          sorted((x['i'], x['saved']) for x in entries() if x['acc'] == m1.acc), [(1, 1), (2, 2)])
    setter(m1, 2, 1, 0)
    check('... a group write to the second part kept aside (still hidden)', drawn(m1), [1, 0, 0, 1, 1])
    r = mv(m1, hair, 1, 1)
    check('... shown (Visible 1): both parts forced shown, one entry each', (r['hits'], drawn(m1),
                                                                          len(entries())), (2, [1, 1, 1, 1, 1], 2))
    r = mv(m1, hair, 2, 0)
    check('... Visible 2 ends both: the bytes back (the second part: the group\'s write kept aside)',
          (r['hits'], entries(), [m1.byte(i) & 3 for i in range(len(NAMES))]),
          (2, [], [b0[0] & 3, b0[1] & 3, 1, b0[3] & 3, b0[4] & 3]))
    m1.set_byte(2, 0x26)
    pm.mem_write(m1.names + 0x40 * 2, b'MarioD_hair_O_OBJ\0')
    r = mv(m1, hair, 0, 0)
    check('v2: two entries with the same name: both hidden', (r['hits'], drawn(m1)), (2, [1, 0, 0, 1, 1]))
    mv(m1, -1, 0, 0)
    check('... Mesh -1 ends both', (entries(), drawn(m1)), ([], [1, 1, 1, 1, 1]))
    pm.mem_write(m1.names + 0x40 * 2, NAMES[2].encode() + b'\0')
    r = mv(m1, MV.crc32('stethoscope_VIS_O_OBJ'), 0, 0)
    check('... a one-part mesh followed by a named one: only it', (r['hits'], drawn(m1)), (1, [0, 1, 1, 1, 1]))
    mv(m1, -1, 0, 0)

    # the clear chain
    mv(m0, MV.crc32('Gamemodel'), 0, 1)
    mv(m1, MV.crc32('stethoscope_VIS_O_OBJ'), 0, 1)
    check('two overrides, drawn hidden', (len(entries()), drawn(m0)[4], drawn(m1)[0]), (2, 0, 0))
    for r_ in range(14, 32):
        pm.reg_write(REG(r_), 0x4000 + r_)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, 0x7F00BB00)
    pm.reg_write(UC_PPC_REG_10, 0x10)
    pm.reg_write(UC_PPC_REG_LR, RET)
    ensure(pm, 0x102F7020, 0x102F7024)
    pm.emu_start(OL.SLOW_CLEAR, OL.CLEAR_BACK, count=200000)
    check('clear (training reset / match start / end): back at 0x02FB349C, r3 / r10 / LR kept, every override off, '
          'the bytes back', (pm.reg_read(UC_PPC_REG_PC), pm.reg_read(UC_PPC_REG_3), pm.reg_read(UC_PPC_REG_10),
                             pm.reg_read(UC_PPC_REG_LR), r32(pm, g), entries(), drawn(m0), drawn(m1)),
          (OL.CLEAR_BACK, 0x7F00BB00, 0x10, RET, 0, [], [1, 1, 0, 1, 1], [1, 1, 1, 1, 1]))
    check('the setter with no override: as the game\'s (bounds: mesh 9 -> 0)', setter(m0, 9, 1, 0), 0)
    check('counter: group writes kept aside (one in the two-part test)', r32(pm, g + 0x18), 3)
    check('CRC32 in the cave = zlib\'s (Gamemodel)', crc_run(pm, lab, m0.names + 0x40 * 4), zlib.crc32(b'Gamemodel'))
    diag_tests(exe, orig)
    sys.exit(1 if acmd_ext_test.fails else 0)


def crc_run(pm, lab, s):
    run(pm, lab['mv_crc'], RET, {UC_PPC_REG_3: s})
    return pm.reg_read(UC_PPC_REG_3)


def diag_tests(exe, orig):
    import diag_godfist_cave as G
    words, lab, _s = MV.build(orig, diag=True)
    check('diag build inside the region', max(a for a in words if a >= MV.CAVE) < MV.LIMIT, True)
    pm = machine(exe)
    for at, w in words.items():
        w32(pm, at, w)
    rec = 0x7F00C000
    ensure(pm, rec, rec + 0x2000)
    st = Asm(G.OSREPORT_VENEER)
    st.asm("""
        lis r12, 0x%X
        ori r12, r12, 0x%X
        lwz r11, 0(r12)
        addi r0, r11, 1
        stw r0, 0(r12)
        slwi r11, r11, 5
        add r12, r12, r11
        stw r3, 0x20(r12)
        stw r4, 0x24(r12)
        stw r5, 0x28(r12)
        stw r6, 0x2C(r12)
        stw r7, 0x30(r12)
        stw r8, 0x34(r12)
        stw r9, 0x38(r12)
        stw r10, 0x3C(r12)
        blr
""" % (rec >> 16, rec & 0xFFFF))
    for i, x in enumerate(st.words()):
        w32(pm, G.OSREPORT_VENEER + 4 * i, x)
    pm.reg_write(UC_PPC_REG_MSR, pm.reg_read(UC_PPC_REG_MSR) | 0x2000)
    ensure(pm, W0, W0 + 0x10000)
    m0 = Model(pm, 0, put_stubs(pm))
    w32(pm, STATE + 4, 0x1000)
    w32(pm, STATE + 8, 0xFFFFFFFF)
    pm.mem_write(FLAG + 8, b'\x01')
    pm.mem_write(PARAMS, struct.pack('>iIii', 0, MV.crc32('Gamemodel'), 0, 1))
    run(pm, lab['h_meshvis'], RET, {UC_PPC_REG_3: m0.acc, UC_PPC_REG_5: STATE, UC_PPC_REG_6: FLAG,
                                     UC_PPC_REG_7: PARAMS})
    ensure(pm, SMGR, SMGR + 0x1000)
    pm.mem_write(SMGR, b'\0' * 0xE80)
    pm.reg_write(UC_PPC_REG_1, 0x7F00F000)
    pm.reg_write(UC_PPC_REG_3, SMGR)
    pm.reg_write(UC_PPC_REG_LR, RET)
    pm.emu_start(OL.TICK_AT, OL.TICK_AT + 4, count=200000)
    n = r32(pm, rec)
    got = [(bytes(pm.mem_read(r32(pm, rec + 0x20 * (i + 1)), 4)).decode('latin1'),
            r32(pm, rec + 0x20 * (i + 1) + 8)) for i in range(n)]
    check('diag: S4MH at the mesh changed (named: part 0), S4MC at the command (the mesh CRC), S4MF at the tick '
          '(entry 0)', got, [('S4MH', 0), ('S4MC', MV.crc32('Gamemodel')), ('S4MF', 0)])


if __name__ == '__main__':
    main()
