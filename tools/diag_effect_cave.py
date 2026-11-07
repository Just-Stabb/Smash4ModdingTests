#!/usr/bin/env python3
"""TEMPORARY diagnostic executable (Smash Run step 2c: Plasma Wisp's laser hits but its effect never shows): OSReport
lines from the effect manager for the enemy effect banks (bank >> 8 == 7: 0x700 + enemy kind, e.g. 0x757
mczakoplasmawisp, whose effects the twin's laser / needles / cannon weapons request: 0x02AE08A4 0x7570003, 0x02AE0970
0x7570004, ...), so Cemu's log shows whether the bank is registered, found, and the effect made. Not for the normal
chain build. Prints rpx_patch.py arguments (docs/smash-run-port.md, "Step 2c v2").

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/diag_effect_cave.py --rpx IN.rpx)

Lines (`S4FX <tag> ...`, hex words):
  reg   a bank's registration (0x032F1388, at 0x032F13C0 after its slot lookup 0x032EFEA0(mgr, bank, 1)): bank, slot
        (>= 0x29: none free: category 7 has 10 slots, 26-35), the bank's resource handle (0: no files).
  req   an effect request reaching the bank lookup (0x032F00A0, at 0x032F011C): effect id, slot (>= 0x29: the bank is
        not registered), and when the slot is valid its words +0 bank, +4 eft resource (the .ptcl), +8 the .efc (0:
        not loaded) and the .efc's entry count (u16 +8, read only when the pointer is word-aligned in
        0x10000000-0x7FFFFFFF: MEM2, Extended Memory's too).
  made  the request's end (0x032F0250, `mr r3, r30`): effect id, the instance handle (0: not made: no free
        instance, or 0x0334D8D8 refused it: index >= the .efc's entries, the effect budget, no emitter set).
  mot   (v2) every change_motion_state (0x02DB420C) of Smash Run's Plasma Wisp (kind 0x12): this, its state, the
        motion index (its twin's set order), the rate (bits): whether its laser states (LaserHold / Laser) run.
Every line counts against MAX_LINES (3000). The stubs are diag_stomp_cave.py's (OSReport through the game's veneer
0x0288B4D4; r0, r2-r12, LR, CTR, XER, CR, f0-f13 saved; the replaced word replayed). Space: 0x04BAE000-0x04BAF000
(diag_stomp_cave.py's; zero in exe_v13 / exe_v14).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diag_stomp_cave as B  # noqa: E402

B.MAX_LINES = 3000
NAMES = {'reg': ('bank', 'slot', 'res'),
         'req': ('id', 'slot', 'bank', 'eft', 'efc', 'n'),
         'made': ('id', 'h'),
         'mot': ('this', 'st', 'idx', 'rate')}
B.HOOKS[:] = [
    ('reg', 0x032F13C0, 0x7C751B78,      # mr r21, r3 (r3 slot, r4 bank, r23 the resource)
     """
        srwi r11, r4, 8
        cmpwi r11, 7
        bne skip
        %s
        mr r6, r23
    """ % B.ld('r5', 3)),
    ('req', 0x032F011C, 0x28030029,      # cmplwi r3, 0x29 (r3 slot, r29 id, r28 the manager)
     """
        srwi r11, r29, 24
        cmpwi r11, 7
        bne skip
        mr r4, r29
        %s
        li r6, -1
        li r7, -1
        li r8, -1
        li r9, -1
        cmplwi r5, 0x29
        bge q_done
        slwi r11, r5, 7
        add r11, r11, r28
        addi r11, r11, 0xB8
        lwz r6, 0(r11)
        lwz r7, 4(r11)
        lwz r8, 8(r11)
        srwi r12, r8, 28
        cmplwi r12, 1
        blt q_done
        cmplwi r12, 7
        bgt q_done
        andi. r12, r8, 3
        bne q_done
        lhz r9, 8(r8)
    q_done:
    """ % B.ld('r5', 3)),
    ('made', 0x032F0250, 0x7FC3F378,     # mr r3, r30 (r30 the handle, r29 id)
     """
        srwi r11, r29, 24
        cmpwi r11, 7
        bne skip
        mr r4, r29
        mr r5, r30
    """),
    # v2: Behavior::change_motion_state 0x02DB420C (r3 this, r4 the motion index, f2 the rate) for Smash Run's
    # Plasma Wisp (kind 0x12, on its twin's behaviour): which of its states run (the twin's set order: Laser /
    # LaserHold, Needle / NeedleHold, Cannon / CannonHold ...)
    ('mot', 0x02DB420C, 0x9421FFB8,      # stwu r1, -0x48(r1)
     """
        lwz r11, 8(r3)
        cmpwi r11, 0x12
        bne skip
        mr r6, r4
        mr r4, r3
        lwz r5, 4(r3)
        stfs f2, 8(r1)
        lwz r7, 8(r1)
    """),
]


def fmt_bytes(tag):
    return ('S4FX %s ' % tag + ' '.join('%s=%%X' % k for k in NAMES[tag]) + '\n').encode() + b'\0'


B.fmt_bytes = fmt_bytes
CAVE, LIMIT, HOOKS, build, args = B.CAVE, B.LIMIT, B.HOOKS, B.build, B.args


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', required=True, help='the executable it goes on: hook words checked')
    a = ap.parse_args()
    print(' '.join(args(a.rpx)))


if __name__ == '__main__':
    main()
