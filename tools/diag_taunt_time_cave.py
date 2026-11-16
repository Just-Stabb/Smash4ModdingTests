#!/usr/bin/env python3
"""TEMPORARY diagnostic for the threads / time-command in-game tests (threads_time_test v2): does a fighter's taunt
bind and run its scripts, do the new commands' handlers run, and what do the time commands change. On top of
tools/diag_godfist_cave.py (the S4GF lines a script's SET_FLOAT to 0x0F0003F0 + k prints) and
tools/diag_threads_cave.py (S4TH), it adds OSReport lines:

  `S4ST status=<hex> mod=<hex> m4=<hex> n=<n>`
      a fighter's status change (the MSC status set-up 0x02E882AC, new kind from vt +0x8C at 0x02E88354) to Appeal
      (0x14D) or the smash taunt (0x14E): the MSC side of a taunt.
  `S4MO hash=<hex> found=<0 / 1> script=<hex> from=<hex> r30=<hex> r29=<hex> n=<n>`
      an animcmd agent bound to a script (0x02BEE560's lookup 0x02BEE404 at 0x02BEE580) for one of the six taunt
      motions (AppealHiR / L, AppealSR / L, AppealLwR / L), and the first FIRST_N binds of the session (to show the
      hook runs): found 0 = no script of that hash in the set's files (the agent is cleared). from = 0x02BEE560's
      caller (0x02760864: the motion change 0x027606C0, r30 = the fighter kind, r29 = the set: 0 game, 1 effect,
      2 sound; other callers: r29 / r30 are theirs).
  `S4TC cmd=<n> p0=<hex> p1=<hex> p2=<hex> run=<0 / 1> acc=<hex> n=<n>`
      a new command's handler entered (1 Time_Scale, 2 Target_Time_Scale, 3 Stage_Freeze, 4 Thread_Start; p0-p2
      its parameter words as the script holds them, floats as bits; run 0 = the interpreter's skip pass); at most
      CMD_N lines.
  `S4TS scene=<n> slow=<0 / 1> req=<n> left=<n> extra=<n> stage=<0 / 1> sleft=<n>`
      the time commands' state (acmd_ext_cave.py ts_data), printed by the battle scene's frame (instead of its
      `bl ts_scene` at 0x0309BE54, then ts_scene as before) on its first call and whenever slow / extra / stage changes.

Cemu: Debug > Logging > "Coreinit Logging" checked; the lines go to log.txt. Not for the normal chain build.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_godfist_cave.py --rpx IN.rpx) \\
      $(python3 tools/diag_threads_cave.py --rpx IN.rpx) $(python3 tools/diag_taunt_time_cave.py --rpx IN.rpx)
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import diag_godfist_cave as G  # noqa: E402

CAVE = 0x04BCC000               # free grown .text (zero in exe_v46s: 0x04BC9A34-0x04BD0000; the step-2 diag caves' space)
DATA = 0x04BCF000               # the formats and counters
LIMIT = 0x04BD0000
STATUS_AT = 0x02E88358          # lwz r4, 0(r30) after the new status kind (r3) came from vt +0x8C
STATUS_WORD = 0x809E0000
BIND_AT = 0x02BEE580            # bl 0x02BEE404 (in 0x02BEE560: r3 the set's files, r4 the agent, r5 the hash, r6 0)
BIND_FN = 0x02BEE404
SCENE_AT = 0x0309BE54           # bl ts_scene (exe_v46n's TS_SCENE)
APPEAL = (0x14D, 0x14E)
TAUNTS = [zlib.crc32(n.encode()) & 0xFFFFFFFF for n in
          ('appealhir', 'appealhil', 'appealsr', 'appealsl', 'appeallwr', 'appeallwl')]
FIRST_N = 4
CMD_N = 64
FMTS = {
    'st': b'S4ST status=%X mod=%08X m4=%08X n=%d\n\0',
    'mo': b'S4MO hash=%08X found=%d script=%08X from=%08X r30=%X r29=%X n=%d\n\0',
    'tc': b'S4TC cmd=%d p0=%08X p1=%08X p2=%08X run=%d acc=%08X n=%d\n\0',
    'ts': b'S4TS scene=%d slow=%d req=%d left=%d extra=%d stage=%d sleft=%d\n\0',
}


def handlers():
    """{name: address} of the new commands' handlers and ts_scene / ts_data in an exe_v46n-based executable
    (acmd_ext_cave.py's own build: the same labels)"""
    import acmd_ext_cave as C
    a, _w, _h = C.build()
    labels = {}
    for p in [a] + [getattr(a, 'part%d' % i) for i in range(2, 10) if hasattr(a, 'part%d' % i)]:
        try:
            labels.update(p.labels)
        except Exception:
            pass
    return {k: labels[k] for k in ('h_tscale', 'h_ttscale', 'h_sfreeze', 'h_thread', 'ts_scene', 'ts_data')}


def bl(src, dst, link=True):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0
    return (18 << 26) | (off & 0x3FFFFFC) | (1 if link else 0)


F = 0x180                       # the stubs' frame: r0 8, lr 0xC, cr 0x10, ctr 0x14, xer 0x18, r3-r31 0x20, f0-f13 0xA0
SAVE = """
        stwu r1, -0x180(r1)
        stw r0, 0x8(r1)
        mflr r0
        stw r0, 0xC(r1)
        mfcr r0
        stw r0, 0x10(r1)
        .word 0x7C0902A6                # mfctr r0
        stw r0, 0x14(r1)
        .word 0x7C0102A6                # mfxer r0
        stw r0, 0x18(r1)
        stmw r3, 0x20(r1)
""" + '\n'.join('        stfd f%d, 0x%X(r1)' % (n, 0xA0 + 8 * n) for n in range(14))
RESTORE = '\n'.join('        lfd f%d, 0x%X(r1)' % (n, 0xA0 + 8 * n) for n in range(14)) + """
        lwz r0, 0x18(r1)
        .word 0x7C0103A6                # mtxer r0
        lwz r0, 0x14(r1)
        .word 0x7C0903A6                # mtctr r0
        lwz r0, 0x10(r1)
        mtcrf 0xFF, r0
        lwz r0, 0xC(r1)
        mtlr r0
        lmw r3, 0x20(r1)
        lwz r0, 0x8(r1)
        addi r1, r1, 0x180
"""


def build(orig):
    for i, w in enumerate(G.VENEER_WORDS):
        if w is not None:
            assert orig(G.OSREPORT_VENEER + 4 * i) == w, 'veneer word %d' % i
    h = handlers()
    assert orig(STATUS_AT) == STATUS_WORD, 'status hook 0x%08X: 0x%08X' % (STATUS_AT, orig(STATUS_AT))
    assert orig(BIND_AT) == bl(BIND_AT, BIND_FN), 'bind hook 0x%08X: 0x%08X' % (BIND_AT, orig(BIND_AT))
    assert orig(SCENE_AT) == bl(SCENE_AT, h['ts_scene']), 'scene hook 0x%08X: 0x%08X' % (SCENE_AT, orig(SCENE_AT))
    for k in ('h_tscale', 'h_ttscale', 'h_sfreeze'):
        assert orig(h[k]) == 0x9421FFC0, '%s 0x%08X: 0x%08X' % (k, h[k], orig(h[k]))
    assert orig(h['h_thread']) == 0x9421FFD0, 'h_thread 0x%08X: 0x%08X' % (h['h_thread'], orig(h['h_thread']))
    # data: counters, last state, formats
    fmt_at, blob = {}, b''
    counters = DATA                 # +0 status n, +4 bind n, +8 cmd n, +0xC scene n, +0x10.. last slow / extra / stage
    off = 0x40
    for k, s in FMTS.items():
        fmt_at[k] = DATA + off + len(blob)
        blob += s + b'\0' * (-len(s) % 4)
    D = dict(vh=G.OSREPORT_VENEER >> 16, vl=G.OSREPORT_VENEER & 0xFFFF, crclr=G.CRCLR_CR1EQ,
             ch=counters >> 16, cl=counters & 0xFFFF, bind=BIND_FN, status_back=STATUS_AT + 4,
             ts=h['ts_scene'], tdh=h['ts_data'] >> 16, tdl=h['ts_data'] & 0xFFFF, first=FIRST_N, cmdn=CMD_N,
             a1=APPEAL[0], a2=APPEAL[1])
    for k, at in fmt_at.items():
        D['f%sh' % k], D['f%sl' % k] = at >> 16, at & 0xFFFF
    print_call = """
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X           # the game's OSReport veneer
        mtctr r12
        .word 0x%(crclr)08X
        bctrl""" % D
    taunt_cmp = '\n'.join("""
        lis r0, 0x%X
        ori r0, r0, 0x%X
        cmplw r10, r0
        beq mo_log""" % (t >> 16, t & 0xFFFF) for t in TAUNTS)
    a = Asm(CAVE)
    src = """
# --- S4ST: b from 0x%(status_back)08X - 4: r3 the new status kind, r31 the StatusModule ---------------------------
dtt_status:
        cmplwi r3, %(a1)d
        beq st_log
        cmplwi r3, %(a2)d
        bne st_out
st_log:
""" % D + SAVE + """
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lwz r7, 0(r12)
        addi r7, r7, 1
        stw r7, 0(r12)
        mr r4, r3
        mr r5, r31
        lwz r6, 4(r31)
        lis r3, 0x%(fsth)X
        ori r3, r3, 0x%(fstl)X""" % D + print_call + "\n" + RESTORE + """
st_out:
        lwz r4, 0(r30)
        b 0x%(status_back)08X

# --- S4MO: bl from 0x02BEE580 instead of bl 0x%(bind)08X; returns its r3 ------------------------------------------
dtt_bind:
""" % D + SAVE + """
        bl 0x%(bind)08X
        stw r3, 0x20(r1)                # the lookup's result, given back
        lwz r10, 0x28(r1)               # the hash (r5)
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lwz r11, 4(r12)
        addi r11, r11, 1
        stw r11, 4(r12)
        cmplwi r11, %(first)d
        ble mo_log""" % D + taunt_cmp + """
        b mo_out
mo_log:
        li r5, 1
        cmpwi r3, -1
        bne mo_found
        li r5, 0
mo_found:
        lwz r4, 0x24(r1)                # the agent (r4)
        lwz r6, 4(r4)                   # its script now (0: cleared)
        mr r4, r10
        lwz r7, 0x194(r1)               # 0x02BEE560's saved LR (its frame: 0x10, LR at +0x14)
        lwz r8, 0x8C(r1)                # r30
        lwz r9, 0x88(r1)                # r29
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lwz r10, 4(r12)
        lis r3, 0x%(fmoh)X
        ori r3, r3, 0x%(fmol)X""" % D + print_call + """
mo_out:
""" + RESTORE + """
        blr
"""
    for cmd_n, name, first in ((1, 'h_tscale', 0x9421FFC0), (2, 'h_ttscale', 0x9421FFC0), (3, 'h_sfreeze', 0x9421FFC0),
                               (4, 'h_thread', 0x9421FFD0)):
        src += """
# --- S4TC: b from %(name)s's first word ------------------------------------------------------------------------------
dtt_%(name)s:
""" % dict(name=name) + SAVE + """
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lwz r10, 8(r12)
        cmplwi r10, %(cmdn)d
        bge tc_out_%(name)s
        addi r10, r10, 1
        stw r10, 8(r12)
        li r4, %(n)d
        lwz r5, 0(r7)
        lwz r6, 4(r7)
        lwz r9, 0x20(r1)                # r3 (the accessor)
        lbz r8, 8(r6)
        lwz r6, 0x2C(r1)                # (r6 back: the condition block)
        lbz r8, 8(r6)
        lwz r6, 4(r7)
        lwz r7, 8(r7)
        lis r3, 0x%(ftch)X
        ori r3, r3, 0x%(ftcl)X""" % dict(D, name=name, n=cmd_n) + print_call + """
tc_out_%(name)s:
""" % dict(name=name) + RESTORE + """
        .word 0x%(first)08X
        b 0x%(back)08X
""" % dict(first=first, back=h[name] + 4)
    src += """
# --- S4TS: bl from 0x0309BE54 instead of bl ts_scene; then ts_scene as before (LR the scene's) ----------------------
dtt_scene:
""" + SAVE + """
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lis r11, 0x%(tdh)X
        ori r11, r11, 0x%(tdl)X
        lwz r4, 0xC(r12)
        addi r4, r4, 1
        stw r4, 0xC(r12)
        cmpwi r4, 1
        beq ts_log
        lwz r5, 4(r11)
        lwz r0, 0x10(r12)
        cmpw r5, r0
        bne ts_log
        lwz r5, 0x14(r11)
        lwz r0, 0x14(r12)
        cmpw r5, r0
        bne ts_log
        lwz r5, 0x18(r11)
        lwz r0, 0x18(r12)
        cmpw r5, r0
        beq ts_out
ts_log:
        lwz r5, 4(r11)
        stw r5, 0x10(r12)
        lwz r0, 0x14(r11)
        stw r0, 0x14(r12)
        lwz r0, 0x18(r11)
        stw r0, 0x18(r12)
        lwz r6, 8(r11)
        lwz r7, 0x10(r11)
        lwz r8, 0x14(r11)
        lwz r9, 0x18(r11)
        lwz r10, 0x1C(r11)
        lis r3, 0x%(ftsh)X
        ori r3, r3, 0x%(ftsl)X""" % D + print_call + """
ts_out:
""" + RESTORE + """
        b 0x%(ts)08X
""" % D
    a.asm(src)
    words = a.words()
    assert CAVE + 4 * len(words) <= DATA, 'code 0x%X words' % len(words)
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    data = b'\0' * 0x40 + blob
    assert DATA + len(data) <= LIMIT
    for i in range(0, len(data), 4):
        out[DATA + i] = struct.unpack('>I', data[i:i + 4])[0]
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[STATUS_AT] = bl(STATUS_AT, a.addr('dtt_status'), link=False)
    out[BIND_AT] = bl(BIND_AT, a.addr('dtt_bind'))
    out[SCENE_AT] = bl(SCENE_AT, a.addr('dtt_scene'))
    for name in ('h_tscale', 'h_ttscale', 'h_sfreeze', 'h_thread'):
        out[h[name]] = bl(h[name], a.addr('dtt_' + name), link=False)
    return out, a.labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v46n-based: exe_v46s)')
    args = p.parse_args()
    import kind_expand as K
    img = K.Image(args.rpx)
    words, _labels = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))


if __name__ == '__main__':
    main()
