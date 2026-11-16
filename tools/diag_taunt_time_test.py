#!/usr/bin/env python3
"""Tests tools/diag_taunt_time_cave.py (unicorn, the game's own code) in the threads / time diag executable
(exe_v46s_diag = exe_v46s + diag_godfist_cave + diag_threads_cave + diag_taunt_time_cave):
- S4MO: the game's script bind 0x02BEE560 on a set holding a test game.bin: the six taunt hashes print one line each
  with found 1 and the script the game bound (found 0, agent cleared, for a hash the file hasn't), the first binds
  of the session print too, other hashes after them don't; the lookup's result and the agent are as without the stub;
- S4ST: a status change to Appeal (0x14D) / 0x14E prints its line, others don't; the replaced word still runs;
- S4TC / S4TS: acmd_ext_test.py's ts_tests (Time_Scale / Target_Time_Scale / Stage_Freeze on the game's own slow
  manager, stage stop, SlowModule) and fighter_thread_tests (a thread on the game's fighter step) pass unchanged on the
  diag executable, each handler call prints its S4TC line, the scene its S4TS lines when the state changes;
- every line's registers / stack kept (the checks above run the game's code after the stubs).

  python3 tools/diag_taunt_time_test.py DIAG.rpx VANILLA_TABLES.rpx GAME.bin
      VANILLA_TABLES: an executable with the game's command tables (acmd_ext_test.py's ORIGINAL; exe_v46n will do);
      GAME.bin: an ACMD file holding the taunt scripts (the test game.bin)
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd_ext_cave as C  # noqa: E402
import acmd_ext_test as T  # noqa: E402
import diag_godfist_cave as G  # noqa: E402
import diag_taunt_time_cave as D  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn import UC_HOOK_CODE  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6, \
    UC_PPC_REG_LR, UC_PPC_REG_PC  # noqa: E402

UC_PPC_REG_30 = UC_PPC_REG_3 + 27
UC_PPC_REG_31 = UC_PPC_REG_3 + 28


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        sys.exit(__doc__)
    pm, om = machine(a[0]), machine(a[1])
    calls = []

    def hook(uc, addr, size, _u):
        regs = [uc.reg_read(UC_PPC_REG_3 + i) for i in range(8)]
        fmt = bytes(uc.mem_read(regs[0], 96)).split(b'\0')[0]
        calls.append((fmt.split(b' ')[0].decode(), regs[1:]))
        for r in range(3, 13):
            uc.reg_write(UC_PPC_REG_3 + r - 3, 0xDEAD0000 + r)
        uc.reg_write(UC_PPC_REG_PC, uc.reg_read(UC_PPC_REG_LR))
    pm.hook_add(UC_HOOK_CODE, hook, begin=G.OSREPORT_VENEER, end=G.OSREPORT_VENEER)

    def lines(tag):
        return [c[1] for c in calls if c[0] == tag]

    # --- S4MO: the bind on a set holding GAME.bin
    data = open(a[2], 'rb').read()
    F = 0x60000000
    pm.mem_map(F, 0x100000)
    pm.mem_write(F, data)
    node, holder, agent = F + 0x80000, F + 0x80100, F + 0x80200
    pm.mem_write(node, struct.pack('>II', F, 0))
    pm.mem_write(holder, struct.pack('>I', node))
    names = ['attack11', 'zzz_none', 'attackdash', 'wait1', 'appealhir', 'appealhil', 'appealsr', 'appealsl',
             'appeallwr', 'appeallwl', 'attack12', 'zzz_none2']
    got = []
    for n in names:
        h = zlib.crc32(n.encode()) & 0xFFFFFFFF
        pm.mem_write(agent, b'\0' * 0x40)
        pm.mem_write(agent + 4, struct.pack('>I', 0x1234))
        before = len(calls)
        T.run(pm, 0x02BEE560, RET, {UC_PPC_REG_1: 0x7F00F000, UC_PPC_REG_3: holder, UC_PPC_REG_4: 0x10390000,
                                    UC_PPC_REG_5: agent, UC_PPC_REG_6: h, UC_PPC_REG_30: 0x41, UC_PPC_REG_31 - 2: 0},
              count=200000)
        script = T.r32(pm, agent + 4)
        line = calls[before][1] if len(calls) > before else None
        got.append((n, line is not None, line and (line[0], line[1], line[2] == script, line[3], line[4], line[5]),
                    pm.reg_read(UC_PPC_REG_1)))
    want_lines = {'attack11', 'zzz_none', 'attackdash', 'wait1', 'appealhir', 'appealhil', 'appealsr', 'appealsl',
                  'appeallwr', 'appeallwl'}
    T.check('S4MO: a line for each of the first %d binds and every taunt hash, none for the others after them'
            % D.FIRST_N, [n for n, has, _l, _s in got if has], [n for n in names if n in want_lines])
    T.check('S4MO: the stack back (0x7F00F000) after every bind', set(s for *_x, s in got), {0x7F00F000})
    have = {}
    pmf = acmd_file = None  # noqa: F841
    import acmd
    f = acmd.ACMDFile.load(a[2])
    for n, has, line, _s in got:
        if has:
            h = zlib.crc32(n.encode()) & 0xFFFFFFFF
            have[n] = line
            T.check('S4MO %s: hash, found %d (the file %s it), the agent\'s script in the line, from = the caller '
                    '(RET), r30 / r29 as the caller had them' % (n, h in f.scripts, 'has' if h in f.scripts else 'lacks'),
                    line, (h, int(h in f.scripts), True, RET, 0x41, 0))

    # --- S4ST: a status change
    st = []
    for status in (0x14D, 0x14E, 0x10, 0x14C):
        before = len(calls)
        mod, r30m = 0x103C8000, 0x103C8100
        pm.mem_write(mod, b'\0' * 0x200)
        T.w32(pm, mod + 4, 0x12345678)
        T.w32(pm, r30m, 0xCAFE0000)
        T.run(pm, D.STATUS_AT, D.STATUS_AT + 4, {UC_PPC_REG_1: 0x7F00F000, UC_PPC_REG_3: status,
                                                  UC_PPC_REG_30: r30m, UC_PPC_REG_31: mod})
        st.append((status, len(calls) - before, pm.reg_read(UC_PPC_REG_4), pm.reg_read(UC_PPC_REG_3),
                   pm.reg_read(UC_PPC_REG_1)))
    T.check('S4ST: Appeal 0x14D / 0x14E print one line each, 0x10 / 0x14C none; the replaced lwz r4, 0(r30) runs; '
            'r3 / r1 kept', st, [(0x14D, 1, 0xCAFE0000, 0x14D, 0x7F00F000), (0x14E, 1, 0xCAFE0000, 0x14E, 0x7F00F000),
                                (0x10, 0, 0xCAFE0000, 0x10, 0x7F00F000), (0x14C, 0, 0xCAFE0000, 0x14C, 0x7F00F000)])
    T.check('S4ST lines: status, the module, its +4', [tuple(x[:3]) for x in lines('S4ST')],
            [(0x14D, 0x103C8000, 0x12345678), (0x14E, 0x103C8000, 0x12345678)])

    # --- S4TC / S4TS: the time commands' and threads' own tests on the diag executable
    a_ext, _w, _h = C.build()
    fails0 = T.fails
    n0 = len(calls)
    T.ts_tests(pm, a_ext)
    T.check('acmd_ext_test ts_tests: no failures on the diag executable', T.fails - fails0, 0)
    tc = [x for x in calls[n0:] if x[0] == 'S4TC']
    ts = [x for x in calls[n0:] if x[0] == 'S4TS']
    cmds = [x[1][0] for x in tc]
    T.check('S4TC: a line for every handler call of ts_tests (Time_Scale 1: 10, Stage_Freeze 3: 4, '
            'Target_Time_Scale 2: 5)', (cmds.count(1), cmds.count(3), cmds.count(2)), (10, 4, 5))
    T.check('S4TC Time_Scale(0.5, 0): p0 = 0.5\'s bits, p1 0, run 1', tuple(tc[0][1][:5]) if tc else None,
            (1, 0x3F000000, 0, tc[0][1][3] if tc else 0, 1))
    if not ts or T.r32(pm, 0x02BF2568) != 0x48009415:  # exe_v46u_threads: S4TS is tools/diag_tick_cave.py's (its test)
        T.check('no scene S4TS hooks (exe_v46u_threads: diag_tick_cave.py prints S4TS from the tick)', True, True)
    else:
      T.check('S4TS: scene C\'s first frame prints (site 3, n 1), then only changes (slow / extra / stage)',
              tuple(ts[0][1][:2]) if ts else None, (3, 1))
      T.check('S4TS: a Time_Scale(2) frame shows extra 1, a Stage_Freeze shows stage 1',
              (any(x[1][5] == 1 for x in ts), any(x[1][6] == 1 for x in ts)), (True, True))
      try:
          import ts_scene_sites_test as TS
          n0 = len(calls)
          fails0 = T.fails
          res = TS.scenario(pm, a_ext)
          T.check('exe_v46t_threads: scenes A / B as tools/ts_scene_sites_test.py expects, with the S4TS hooks in place',
                  {k: (v[0], v[1]) for k, v in res.items()},
                  {k: ([(1, 0, True), (2, 1, True), (2, 1, True), (2, 1, True), (1, 0, True)], [1, 1, 0]) for k in res})
          sites = sorted(set(x[1][0] for x in calls[n0:] if x[0] == 'S4TS'))
          T.check('S4TS: scenes A (site 1) and B (site 2) print their lines', sites, [1, 2])
      except AssertionError:
          T.check('ts_scene_sites_cave.py not in this executable (exe_v46s-based diag): scenes A / B not hooked', True, True)
    fails0 = T.fails
    n0 = len(calls)
    cave, _w2, _h2 = C.build()
    for lo, hi in ((0x02BEE63C, 0x02BEE9B8), (0x02BE5500, 0x02BE5B00)):      # (as diag_threads_test.py: the paired-
        for at in range(lo, hi, 4):                                          # single / vector words unicorn can't run)
            if T.r32(pm, at) >> 26 in (4, 56, 57, 60, 61):
                T.w32(pm, at, 0x60000000)
    T.fighter_thread_tests(pm, om, cave, stack_top=0x0E200F50 + 0x20)
    T.check('acmd_ext_test fighter_thread_tests (the stack where the user\'s log has it): no failures on the diag '
            'executable', T.fails - fails0, 0)
    tc = [x for x in calls[n0:] if x[0] == 'S4TC']
    T.check('S4TC: Thread_Start\'s handler printed (cmd 4, ID 9) on each start', sorted(set((x[1][0], x[1][2])
            for x in tc)), [(4, 9)])
    print('%d failures' % T.fails)
    sys.exit(1 if T.fails else 0)


if __name__ == '__main__':
    main()
