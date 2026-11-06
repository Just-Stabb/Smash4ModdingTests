#!/usr/bin/env python3
"""Training: "No. of CPUs" (pause menu, MmelTraining_4) from 0 to 3 instead of 1 to 3; the default stays 1.
Prints rpx_patch.py args (added after the standard build's), or patches an RPX:

  python3 tools/training_cpu_patch.py                    the rpx_patch.py args
  python3 tools/training_cpu_patch.py IN.rpx OUT.rpx     IN with the patch (checks the original word first)

The count is the training menu's setting +0x118 (menu object: ctor 0x02688808, made by the battle HUD
manager only in menu mode 0xB, Training). Its input handler 0x0268A3C8 switches on the cursor (jump table
0x0268A4C0); case 3, the CPU count:

  0x0268A500  addic. r31, r28, 0x118      ; the value
  0x0268A504  li r3, 1                    ; the minimum      -> li r3, 0
  0x0268A508  li r5, 4                    ; one past the maximum
  left  0x0268A620: v - 1, below r3 -> r5 - 1 (wraps to 3)
  right 0x0268A6A8: v + 1, r5 or more -> r3 (wraps to the minimum)

The default comes from the settings reset 0x02687D8C (every training battle start and the menu's Reset):
0x02687D9C stw r10 (1), 8(r3): kept. Everything that reads the count loops up to it (the training controller
0x02FC7C28 spawns entries 1..count and removes the ones above it with the game's own remove call; per-CPU
behaviour / damage loops; start-up 0x02FC90C4; the battle (re)start step 0x02FBA350), so 0 removes the CPU
as 2 -> 1 removes the second one (docs/boot-training.md, "Training: no CPUs").
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SITE = 0x0268A504
ORIGINAL = 0x38600001       # li r3, 1
PATCHED = 0x38600000        # li r3, 0


def args():
    return ['0x%08X=0x%08X' % (SITE, PATCHED)]


def main():
    if len(sys.argv) == 1:
        print(' '.join(args()))
        return
    import rpx_patch
    src, dst = sys.argv[1:3]
    d, _shoff, _ent, secs = rpx_patch.load(src)
    word = rpx_patch.read_u32(d, secs, SITE)
    if word not in (ORIGINAL, PATCHED):
        raise SystemExit('0x%08X holds 0x%08X, not li r3,1: a different executable?' % (SITE, word))
    sys.argv = ['rpx_patch.py', src, dst] + args()
    rpx_patch.main()


if __name__ == '__main__':
    main()
