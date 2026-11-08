#!/usr/bin/env python3
"""More effect-bank slots: the effect manager (0x032EE380, one object, [0x10353CA4]) keeps the registered effect
banks in 41 slots of 0x80 bytes at manager +0xB8, grouped by category (bank >> 8) through two tables read only by the
slot finder 0x032EFEA0: count [0x101906D4 + 4 * cat], first slot [0x10423B2C + 4 * cat] (1 common 0, 2 1, 3 fighters
2-9, 4 Final Smashes 10-17, 5 18-25, 7 enemies 26-35, 9 37-40; 0, 6, 8 none; slot 36 unused). Smash Run's enemy banks
(category 7, 0x700 + kind) ran out at 10. This patch makes 127 slots and gives category 7 the 86 new ones (41-126);
every other category keeps its slots.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx $(python3 tools/effect_slots_patch.py --rpx IN.rpx)
  python3 tools/effect_slots_patch_test.py OUT.rpx IN.rpx

How (immediates only, no new code; docs/native-notes.md "Effect manager: bank slots"):
- The slot array is followed in the manager by the effect-instance pool (+0x1540: 100 x 0x1C0, its live count at
  +0xC440), a mutex (+0xC444) and a 0x1C-byte camera block (+0xC470); the object is 0xC490 bytes. The tail moves up
  by DELTA = 86 x 0x80 and the allocation grows by DELTA, so the slot array grows in place (slot n stays at
  +0xB8 + n * 0x80, the slot pointers handed to the effect instances are unchanged).
- Every reference to the tail in the manager's code (0x032EE09C-0x032F2000; nothing else reads the manager past
  +0x44: the facade 0x0334C3C8-0x0334CC40 and the other users of [0x10353CA4] only call its methods or touch +0x3C /
  +0x40): `addi/lwzu ... 0x1540` (37), the pre-increment loop bases `addi rX, mgr, 0x1380` (5), `addis rX, mgr, 1` +
  `-0x3BC0` (the pool count, 3) / `-0x3BBC` (the mutex, 11, the constructor's also sizes the allocation and the
  camera block), `ori r0, r0, 0xC470` (1).
- Every slot count / bound: the loops over all slots and the slot array's construct / destruct (`li 0x29`: per-frame
  release 0x032EE318, constructor 0x032EE4C4, destructor 0x032EE788, unload-all 0x032EEA64, find-by-bank 0x032F1344,
  unregister-by-bank 0x032F1CD4) and the `cmplwi 0x29` after every slot lookup (0x032EFF80, 0x032F011C request,
  0x032F0638, 0x032F1068 / 0x032F1108 / 0x032F11A8 flag getters, 0x032F13C4 registration, facade 0x0334C500).
- eft: the System's resource table is sized by the manager's config (0x032EF850 `li r0, 0x29` -> config +0x18; eft
  makes +0x18 + +0x2C (0x20) entries at System +8, 0x04A5374C), and a bank's eft resource id is its slot
  (0x032F164C -> 0x04A55160, no bound there; 0x04A55BF0 checks id < System +0xC): 127 + 32 entries.
- The category tables: category 7's count 10 -> 86 (0x101906F0), first 26 -> 41 (0x10423B48).
Handles are (pool index << 24) | a serial (0x032F01E0): no slot in them. Slot numbers are only words (the finder's
result, slot +4 the eft resource id); 127 keeps them below 0x80.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OLD_SLOTS, NEW_SLOTS = 41, 127
SLOT_SIZE, SLOTS_AT = 0x80, 0xB8
ENEMY_CAT, ENEMY_FIRST = 7, OLD_SLOTS
ENEMY_COUNT = NEW_SLOTS - OLD_SLOTS                 # 86
DELTA = ENEMY_COUNT * SLOT_SIZE                     # 0x2B00: the manager's tail moves up by this
MGR_SIZE = 0xC490
POOL, POOL_COUNT, MUTEX, CAMERA = 0x1540, 0xC440, 0xC444, 0xC470
CAT_COUNT, CAT_FIRST = 0x101906D4, 0x10423B2C       # per-category tables (words), read only by 0x032EFEA0
CODE_RANGE = (0x032EE09C, 0x032F2000)                # the manager's methods
FACADE_RANGE = (0x0334C3C8, 0x0334CC40)

COUNT_SITES = [0x032EE318, 0x032EE4C4, 0x032EE788, 0x032EEA64, 0x032EF850, 0x032EFF80, 0x032F011C, 0x032F0638,
               0x032F1068, 0x032F1108, 0x032F11A8, 0x032F1344, 0x032F13C4, 0x032F1CD4, 0x0334C500]
POOL_SITES = [0x032EE4DC, 0x032EE75C, 0x032EFB28, 0x032EFC74, 0x032EFD64, 0x032F0194, 0x032F0208, 0x032F02BC,
              0x032F040C, 0x032F0524, 0x032F0760, 0x032F0798, 0x032F07EC, 0x032F08C0, 0x032F0904, 0x032F0994,
              0x032F0A10, 0x032F0A64, 0x032F0AE4, 0x032F0B4C, 0x032F0BCC, 0x032F0C24, 0x032F0C5C, 0x032F0C94,
              0x032F0CCC, 0x032F0D00, 0x032F0D34, 0x032F0D68, 0x032F0E0C, 0x032F0E44, 0x032F0EE8, 0x032F0F6C,
              0x032F1024, 0x032F125C, 0x032F12FC, 0x032F1DCC, 0x032F1E04]              # 0x1540
POOL_PRE_SITES = [0x032EE82C, 0x032EE940, 0x032F0348, 0x032F0494, 0x032F05EC]          # 0x1380 (+0x1C0 lwzu)
COUNT_FIELD_SITES = [0x032EE0B0, 0x032F00DC, 0x032F1D3C]                              # -0x3BC0 after addis 1
MUTEX_SITES = [0x032EE1F0, 0x032EE3A8, 0x032EE81C, 0x032EE930, 0x032EFD1C, 0x032F0294, 0x032F0338, 0x032F03E4,
               0x032F0484, 0x032F05DC, 0x032F1628]                                    # -0x3BBC after addis / lis 1
CAMERA_SITES = [0x032EFB88]                                                            # ori r0, r0, 0xC470

# the base words (vanilla; unchanged in exe_v17)
ORIGINAL = {
    0x032EE318: 0x3BA00029, 0x032EE4C4: 0x38800029, 0x032EE788: 0x38800029, 0x032EEA64: 0x3BA00029,
    0x032EF850: 0x38000029, 0x032EFF80: 0x28030029, 0x032F011C: 0x28030029, 0x032F0638: 0x28080029,
    0x032F1068: 0x28030029, 0x032F1108: 0x28030029, 0x032F11A8: 0x28030029, 0x032F1344: 0x39200029,
    0x032F13C4: 0x28150029, 0x032F1CD4: 0x39400029, 0x0334C500: 0x28030029,
    0x032EE4DC: 0x387F1540, 0x032EE75C: 0x387E1540, 0x032EFB28: 0x3BBF1540, 0x032EFC74: 0x3BE31540,
    0x032EFD64: 0x3BBC1540, 0x032F0194: 0x397C1540, 0x032F0208: 0x397C1540, 0x032F02BC: 0x84031540,
    0x032F040C: 0x84031540, 0x032F0524: 0x840C1540, 0x032F0760: 0x840C1540, 0x032F0798: 0x840C1540,
    0x032F07EC: 0x84031540, 0x032F08C0: 0x840C1540, 0x032F0904: 0x84EC1540, 0x032F0994: 0x850C1540,
    0x032F0A10: 0x840C1540, 0x032F0A64: 0x856C1540, 0x032F0AE4: 0x840C1540, 0x032F0B4C: 0x840C1540,
    0x032F0BCC: 0x854C1540, 0x032F0C24: 0x84031540, 0x032F0C5C: 0x84031540, 0x032F0C94: 0x84031540,
    0x032F0CCC: 0x84031540, 0x032F0D00: 0x84031540, 0x032F0D34: 0x84031540, 0x032F0D68: 0x84031540,
    0x032F0E0C: 0x84031540, 0x032F0E44: 0x854C1540, 0x032F0EE8: 0x840C1540, 0x032F0F6C: 0x84031540,
    0x032F1024: 0x84031540, 0x032F125C: 0x841F1540, 0x032F12FC: 0x841F1540, 0x032F1DCC: 0x840C1540,
    0x032F1E04: 0x840C1540,
    0x032EE82C: 0x3BFC1380, 0x032EE940: 0x3BFF1380, 0x032F0348: 0x3BFF1380, 0x032F0494: 0x3BFF1380,
    0x032F05EC: 0x3BF41380,
    0x032EE0B0: 0x916AC440, 0x032F00DC: 0x3BDEC440, 0x032F1D3C: 0x9009C440,
    0x032EE1F0: 0x3B9CC444, 0x032EE3A8: 0x3B9CC444, 0x032EE81C: 0x3BDEC444, 0x032EE930: 0x3BDEC444,
    0x032EFD1C: 0x3B7BC444, 0x032F0294: 0x3BDEC444, 0x032F0338: 0x3B5AC444, 0x032F03E4: 0x3B5AC444,
    0x032F0484: 0x3B18C444, 0x032F05DC: 0x3866C444, 0x032F1628: 0x3A94C444,
    0x032EFB88: 0x6000C470,
    CAT_COUNT + 4 * ENEMY_CAT: 10, CAT_FIRST + 4 * ENEMY_CAT: 26,
}


def _imm(word, value):
    return (word & 0xFFFF0000) | (value & 0xFFFF)


def _simm(word):
    v = word & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def patches():
    p = {}
    for a in COUNT_SITES:
        assert ORIGINAL[a] & 0xFFFF == OLD_SLOTS
        p[a] = _imm(ORIGINAL[a], NEW_SLOTS)
    for a in POOL_SITES + POOL_PRE_SITES + COUNT_FIELD_SITES + MUTEX_SITES:
        v = _simm(ORIGINAL[a]) + DELTA                   # a signed displacement / addi: must stay in range
        assert -0x8000 <= v < 0x8000, hex(a)
        p[a] = _imm(ORIGINAL[a], v)
    for a in CAMERA_SITES:
        v = (ORIGINAL[a] & 0xFFFF) + DELTA               # ori (unsigned) after lis r0, 0
        assert v < 0x10000
        p[a] = _imm(ORIGINAL[a], v)
    p[CAT_COUNT + 4 * ENEMY_CAT] = ENEMY_COUNT
    p[CAT_FIRST + 4 * ENEMY_CAT] = ENEMY_FIRST
    assert set(p) == set(ORIGINAL)
    return p


def check_base(rpx):
    import kind_expand as K
    img = K.Image(rpx)
    p = patches()
    bad = ['0x%08X: 0x%08X' % (a, img.w(a)) for a, w in ORIGINAL.items() if img.w(a) not in (w, p[a])]
    if bad:
        raise SystemExit('effect_slots_patch: unexpected words in %s: %s' % (rpx, ', '.join(bad)))


def args():
    return ['0x%08X=0x%08X' % (a, w) for a, w in sorted(patches().items())]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--rpx', help='check the base words in this RPX first (vanilla, or this patch\'s)')
    a = ap.parse_args()
    if a.rpx:
        check_base(a.rpx)
    print(' '.join(args()))


if __name__ == '__main__':
    main()
