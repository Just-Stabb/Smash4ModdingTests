#!/usr/bin/env python3
"""TEMPORARY diagnostic for exe_v46u_threads (threads / time test v3), with tools/diag_godfist_cave.py,
diag_threads_cave.py and diag_taunt_time_cave.py (its S4ST / S4MO / S4TC lines; its scene hooks are off there):

  `S4TS from=<hex> n=<n> slow=<0 / 1> req=<n> left=<n> extra=<n> stage=<0 / 1>`
      tools/ts_tick_cave.py's tick (bl tsu_frame at 0x02BF2568, the battle object world's first phase): on its first
      call, the first call from each battle step (from = 0x02BF2544's caller: 0x02910F2C the step 0x029108D0 of scenes
      A / B / C, 0x02913E08 the step 0x02913310, 0x02FF4F50 the battle sequence's frame 0x02FF4DF8), and whenever
      slow / extra / stage changes: which per-frame path the match runs and the time state.
  `S4GE eff=<hex> gate9f=<n> gatea0=<n> run=<0 / 1> acc=<hex> n=<n>`
      a Graphic_Effect (the EFFECT handler 0x02BE1444): the only effect command that checks EffectModule vt +0x32C,
      which refuses the request when its byte +0x9F or +0xA0 is set; at most GE_N lines.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_godfist_cave.py --rpx IN.rpx) \\
      $(python3 tools/diag_threads_cave.py --rpx IN.rpx) $(python3 tools/diag_taunt_time_cave.py --rpx IN.rpx) \\
      $(python3 tools/diag_tick_cave.py --rpx IN.rpx)
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import diag_godfist_cave as G  # noqa: E402
import diag_taunt_time_cave as DT  # noqa: E402
import ts_tick_cave as U  # noqa: E402

CAVE = 0x04BCD000               # after diag_taunt_time_cave.py's code (0x04BCC000-), before its data (0x04BCF000-)
DATA = 0x04BCF800
LIMIT = 0x04BD0000
GE_AT = 0x02BE1444              # Graphic_Effect's handler: stwu r1, -0x70(r1)
GE_WORD = 0x9421FF90
GE_N = 64
FMTS = {'ts': b'S4TS from=%08X n=%d slow=%d req=%d left=%d extra=%d stage=%d\n\0',
        'ge': b'S4GE eff=%08X gate9f=%d gatea0=%d run=%d acc=%08X n=%d\n\0'}


def bl(src, dst, link=True):
    off = dst - src
    assert -0x2000000 <= off < 0x2000000 and off % 4 == 0, '0x%08X -> 0x%08X' % (src, dst)
    return (18 << 26) | (off & 0x3FFFFFC) | (1 if link else 0)


def build(orig):
    w = orig(U.FRAME_AT)
    assert w >> 26 == 18 and w & 1, 'no tick call at 0x%08X' % U.FRAME_AT
    off = w & 0x3FFFFFC
    tsu_frame = U.FRAME_AT + (off - 0x4000000 if off & 0x2000000 else off)
    assert U.CAVE <= tsu_frame < U.LIMIT, 'not exe_v46u_threads (0x%08X)' % tsu_frame
    assert orig(GE_AT) == GE_WORD, 'Graphic_Effect handler 0x%08X: 0x%08X' % (GE_AT, orig(GE_AT))
    import ts_tick_cave
    td = ts_tick_cave.labels()['ts_data']
    fmt_at, blob = {}, b''
    for k, s in FMTS.items():
        fmt_at[k] = DATA + 0x40 + len(blob)
        blob += s + b'\0' * (-len(s) % 4)
    D = dict(vh=G.OSREPORT_VENEER >> 16, vl=G.OSREPORT_VENEER & 0xFFFF, crclr=G.CRCLR_CR1EQ,
             ch=DATA >> 16, cl=DATA & 0xFFFF, tdh=td >> 16, tdl=td & 0xFFFF, tsu=tsu_frame, gen=GE_N,
             ge_back=GE_AT + 4)
    for k, at in fmt_at.items():
        D['f%sh' % k], D['f%sl' % k] = at >> 16, at & 0xFFFF
    pc = """
        lis r12, 0x%(vh)X
        ori r12, r12, 0x%(vl)X
        mtctr r12
        .word 0x%(crclr)08X
        bctrl""" % D
    # DATA: +0 n, +4 ge n, +8.. last slow / extra / stage, +0x14.. 4 callers seen
    src = """
# --- S4TS: bl from 0x02BF2568 instead of bl tsu_frame; then tsu_frame as before (LR the world phase's) -------------
dtk_frame:
""" + DT.SAVE + """
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lis r11, 0x%(tdh)X
        ori r11, r11, 0x%(tdl)X
        lwz r5, 0(r12)
        addi r5, r5, 1
        stw r5, 0(r12)
        lwz r4, 0x19C(r1)               # 0x02BF2544's saved LR (its frame 0x18, LR at +0x1C): the battle step
        li r10, 0
dk_find:
        slwi r9, r10, 2
        add r9, r9, r12
        lwz r0, 0x14(r9)
        cmplw r0, r4
        beq dk_known
        cmpwi r0, 0
        beq dk_new
        addi r10, r10, 1
        cmpwi r10, 4
        blt dk_find
        b dk_known
dk_new:
        stw r4, 0x14(r9)
        b dk_log
dk_known:
        lwz r6, 4(r11)
        lwz r0, 8(r12)
        cmpw r6, r0
        bne dk_log
        lwz r6, 0x14(r11)
        lwz r0, 0xC(r12)
        cmpw r6, r0
        bne dk_log
        lwz r6, 0x18(r11)
        lwz r0, 0x10(r12)
        cmpw r6, r0
        beq dk_out
dk_log:
        lwz r6, 4(r11)
        stw r6, 8(r12)
        lwz r0, 0x14(r11)
        stw r0, 0xC(r12)
        lwz r0, 0x18(r11)
        stw r0, 0x10(r12)
        lwz r7, 8(r11)
        lwz r8, 0x10(r11)
        lwz r9, 0x14(r11)
        lwz r10, 0x18(r11)
        lis r3, 0x%(ftsh)X
        ori r3, r3, 0x%(ftsl)X""" % D + pc + """
dk_out:
""" + DT.RESTORE + """
        b 0x%(tsu)08X

# --- S4GE: b from Graphic_Effect's handler (r3 the accessor, r6 the run block, r7 the parameters) ------------------
dtk_ge:
""" % D + DT.SAVE + """
        lis r12, 0x%(ch)X
        ori r12, r12, 0x%(cl)X
        lwz r10, 4(r12)
        cmplwi r10, %(gen)d
        bge ge_out
        addi r10, r10, 1
        stw r10, 4(r12)
        lwz r4, 0(r7)                   # the effect id
        lbz r7, 8(r6)                   # run
        mr r8, r3                       # the accessor
        mr r9, r10                      # n
        lwz r11, 0xA0(r3)               # its EffectModule
        li r5, -1
        li r6, -1
        cmpwi r11, 0
        beq ge_print
        lbz r5, 0x9F(r11)
        lbz r6, 0xA0(r11)
ge_print:
        lis r3, 0x%(fgeh)X
        ori r3, r3, 0x%(fgel)X""" % D + pc + """
ge_out:
""" + DT.RESTORE + """
        stwu r1, -0x70(r1)
        b 0x%(ge_back)08X
""" % D
    a = Asm(CAVE)
    a.asm(src)
    words = a.words()
    assert CAVE + 4 * len(words) <= DATA
    out = {CAVE + 4 * i: x for i, x in enumerate(words)}
    data = b'\0' * 0x40 + blob
    assert DATA + len(data) <= LIMIT
    for i in range(0, len(data), 4):
        out[DATA + i] = struct.unpack('>I', data[i:i + 4])[0]
    for x in out:
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out[U.FRAME_AT] = bl(U.FRAME_AT, a.addr('dtk_frame'))
    out[GE_AT] = bl(GE_AT, a.addr('dtk_ge'), link=False)
    return out, a.labels


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', required=True, help='the executable to patch (exe_v46u_threads)')
    args = p.parse_args()
    import kind_expand as K
    img = K.Image(args.rpx)
    words, _l = build(img.w)
    print(' '.join('0x%08X=0x%08X' % kv for kv in sorted(words.items())))


if __name__ == '__main__':
    main()
