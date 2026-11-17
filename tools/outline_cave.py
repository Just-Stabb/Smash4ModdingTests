#!/usr/bin/env python3
"""Outline_Set (model_commands v1, exe_v46z_outline): a coloured glow on an object's silhouette edges (a fresnel rim),
optionally with a body tint, faded in / out and pulsing, on any fighter or article. Supamario's Time Skip needs XV2's
BPE 85 "Flashing White Body Outline". Prints rpx_patch.py arguments for an executable with exe_v46z_inv's patches (or
any later chain of the same caves); asserts every word it replaces.

  python3 tools/rpx_patch.py exe_v46z_inv.rpx exe_v46z_ol.rpx $(python3 tools/outline_cave.py --rpx exe_v46z_inv.rpx)
  python3 tools/outline_cave.py --labels tools/Sm4shCommand/param_labels.json     (Sm4shCommand's entry)

How Smash 4 draws a fighter's rim (read from shader/texas_cross.nsh and cross_f.rpx; docs/native-notes.md "Outline"):
  - Every lit fighter shader (0x94... / 0x96... / 0x9A... families) has a fresnel rim term in its pixel program:
      rim = (1 - N.V) ^ (fresnelParams.x + 1) x (vsRim x sat + g_fresnelOffset.rgb) x clamp(N.y + 1)
    added to the lit colour before the overlay (blinkColor) mix. fresnelParams / fresnelColor are the material's
    (NU_fresnelParams / NU_fresnelColor, uniform block MC, CB4: per material, fixed); vsRim = fresnelColor x
    g_fresnelColor (the vertex program); g_fresnelColor / g_fresnelOffset are in uniform block FB1 (CB7, 0x2A0
    bytes: blinkColor +0x40, spycloakParams +0x80, compressParam +0x90, g_fresnelColor +0xA0, g_fresnelOffset
    +0x1D0, characterColor +0x290, the model's lights).
  - FB1 is the model instance's own buffer (MI + 0x2A0), rebuilt every frame by the instance's vt +0x2C (0x0341E038
    for one model class, 0x03423E78 for the other): locked (vt +0x3C), cleared (DCZeroRange), filled (blinkColor from
    the instance's colours, the lights, ...), unlocked (vt +0x44). So a per-object override is one more write into
    that buffer just before its unlock: g_fresnelOffset += colour x strength x weight (the glow at the edges only;
    the material's own exponent decides how far in it reaches), and, for a body tint, blinkColor mixed toward the
    colour (the overlay's own formula: c' = c (1 - a) + rgb a).
  - The object -> instance: accessor +0x3C ModelModule, +4 its model handle, handle +8 the instance (0x032FF668 /
    0x032FF68C read it so): MI = [[acc + 0x3C] + 0xC].
  - 120 of the 187 lit shaders with a rim read g_fresnelOffset (every one Dr. Mario uses: 0x9601106B, 0x9A011063,
    0x9A211067, 0x9AE11165); the 0x...3063 / 0x...5061 family (a second rim model) and unlit ones (0x92...) don't:
    their meshes get no glow (the tint still shows).

Command: Outline_Set(Target, Red, Green, Blue, Alpha, Tint, Frames, FadeIn, FadeOut, Flash) (index OL_INDEX, CRC of
the name), 11 words. One outline per object (a new one replaces it, fading from where it is).
  Target     whose: 0 this object, 1 nearest opponent, 2 last fighter hit, 3-10 slots 1-8, 11 last attacker, 12 the
             fighter this attack hit (acmd_ext's targets).
  Red/Green/Blue  the glow's colour, 0-255.
  Alpha      its strength: 255 the colour at full at the very edge; up to 1020 (4x) for a hard glow; 0 ends the
             outline (fading out over this command's FadeOut).
  Tint       a body tint toward the colour too, 0-255 (0: edge only).
  Frames     held this many frames once faded in, then fades out over FadeOut; 0 until Alpha 0, a KO or the match end.
  FadeIn / FadeOut  frames (0 at once).
  Flash      a pulse: one cycle every Flash frames (full -> off -> full, smooth); 0 steady.

Hooks (each word asserted):
  FB_A  0x0341E2C0 / 0x0341E2DC  bctrl (the FB1 unlock, model class A: r30 the instance, r28 the locked FB1) -> ol_fbA
  FB_B  0x034247B0 / 0x0342484C  bctrl (class B: r31 the instance, r27 FB1) -> ol_fbB
        both: the outline written into FB1, then the unlock (r3 / CTR / the return address the game's)
  TICK  0x032EFB78  bl (the screen-effect manager's update, now screen_invert's si_tick) -> ol_tick: the earlier
        tick, then the outlines' frame (fades, Frames, the pulse; a KO (fighter status 0xB1) or an object whose model
        changed drops its outline)
  CLEAR the slow-motion clear-all chain's last `b 0x02FB349C` (screen_invert's si_clear: training reset, restart,
        match start / end) -> ol_clear: every outline off, then on
  LOOKUP / SIZE1 / SIZE2 / FETCH: as tools/screen_invert_cave.py (chained in front of the earlier caves' fallbacks).
  --diag: TEST ONLY OSReport lines (S4OC per command; S4OT the outline's frame and S4OF the FB1 write: the first 30
  frames after a command, then every 30th).
Space: 0x04BE3000-0x04BE4000 (docs/native-notes.md "Outline": past the screen invert's, the text region grown).
Test: tools/outline_test.py (unicorn: the game's FB1 builder 0x0341E038 up to its unlock, the tick through the game's
code, the handler, the tables).
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402
import line_test_cave as LT  # noqa: E402

CAVE, LIMIT = 0x04BE3000, 0x04BE4000
TEXT_REGION = LIMIT - 0x02000000
OL_INDEX = 2400                 # (Screen_Invert 2300)
CMD_NAME = 'Outline_Set'
CMD_CRC = zlib.crc32(CMD_NAME.encode()) & 0xFFFFFFFF
NPARAMS = 10
N_ENT, ENT = 16, 0x50

FB_A = (0x0341E2C0, 0x0341E2DC)  # bctrl: FB1 unlock, class A (r30 MI, r28 data)
FB_B = (0x034247B0, 0x0342484C)  # bctrl: class B (r31 MI, r27 data)
FB_SIG = {0x0341E2A0: 0x807E02A0, 0x0341E2AC: 0x80EB0044, 0x0341E2C8: 0x807E02A0, 0x0341E2D0: 0x80EB0044,
          0x0341E0DC: 0x7C7C1B78, 0x0341E0D8: 0x388002A0,
          0x034247A0: 0x807F02A0, 0x034247A8: 0x80A40044, 0x0342483C: 0x807F02A0, 0x03424844: 0x80A40044,
          0x03423F28: 0x7C7B1B78, 0x03423F24: 0x388002A0}
FB_BUILDERS = {0x101A0128 + 0x2C: 0x0341E038, 0x101A0338 + 0x2C: 0x03423E78}   # MI vtables' +0x2C
BLINK, FRES_OFF = 0x40, 0x1D0   # FB1: blinkColor, g_fresnelOffset (bytes)
FB1_SIZE = 0x2A0
TICK_AT = 0x032EFB78
SCREEN_UPD = 0x0334B250
CLEAR_BACK = 0x02FB349C
SLOW_CLEAR = 0x02FB3498
TSU_CLEAR_END = 0x3C
NC_TARGET = 0x04B98A00          # acmd_ext_cave.py's nc_target(r3 accessor, r4 target) -> r3 accessor or 0
NC_TARGET_SIG = (0x2C040000, 0x40820008, 0x4E800020, 0x9421FFE0)
FIGHTER_SM_VT = 0x1012D42C      # the fighters' StatusModule vtable (var_reset_cave.py)
DEAD = 0xB1                     # the fighters' dead status kind
CAVES_LO, CAVES_HI = 0x04B70000, 0x04C00000
DIAG_EVERY = 30


def _bl_target(at, w):
    if w >> 26 != 18 or w & 3 != 1:
        return None
    off = w & 0x3FFFFFC
    return at + (off - 0x4000000 if off & 0x2000000 else off)


def clear_tail(orig):
    """the clear-all chain's last word: tsu_clear's end, followed through every cave's clear (each ends with a `b`
    to the next or to 0x02FB349C) -> (address of the `b 0x02FB349C`, its word)"""
    w = orig(SLOW_CLEAR)
    assert w >> 26 == 18 and not w & 3, 'slow clear 0x%08X: 0x%08X (want ts_tick_cave.py\'s b tsu_clear)' % (
        SLOW_CLEAR, w)
    at = LT.bdecode(SLOW_CLEAR, w) + TSU_CLEAR_END
    assert orig(at - 4) == 0x39400010, 'tsu_clear: no li r10, 0x10 at 0x%08X' % (at - 4)
    for _ in range(16):
        w = orig(at)
        assert w >> 26 == 18 and not w & 3, 'clear chain 0x%08X: 0x%08X (want a b)' % (at, w)
        to = LT.bdecode(at, w)
        if to == CLEAR_BACK:
            return at
        assert CAVES_LO <= to < CAVES_HI, 'clear chain 0x%08X -> 0x%08X' % (at, to)
        for x in range(to, to + 0x200, 4):         # that cave's clear: its first b (not bl) out of it
            y = orig(x)
            if y >> 26 == 18 and not y & 3 and not (to <= LT.bdecode(x, y) < to + 0x200):
                at = x
                break
        else:
            raise AssertionError('clear chain: no way out of 0x%08X' % to)
    raise AssertionError('clear chain too long')


def tick_prev(orig):
    t = _bl_target(TICK_AT, orig(TICK_AT))
    assert t is not None and (t == SCREEN_UPD or CAVES_LO <= t < CAVES_HI), 'tick 0x%08X: 0x%08X' % (
        TICK_AT, orig(TICK_AT))
    return t


def table_find(orig, lo, hi):
    """the command tables' fallbacks (line_test_cave.find), refused when they already point into [lo, hi)"""
    s = LT.find(orig)
    for k in ('lk_none', 's1', 's2', 'f'):
        if s[k + '_word'] >> 26 == 18:
            assert not lo <= LT.bdecode(s[k], s[k + '_word']) < hi, 'already patched (%s)' % k
    return s


def table_src(s, prefix, base, crc, size, hand):
    """the 4 command-table fallbacks for one new command (index base, CRC crc, size words), chained in front of the
    earlier caves' (as tools/screen_invert_cave.py)"""
    D = dict(p=prefix, base=base, crc_h=crc >> 16, crc_l=crc & 0xFFFF, s1b=s['s1_back'], s2b=s['s2_back'],
             fb=s['f_back'], hand_h=hand >> 16, hand_l=hand & 0xFFFF, size=size)
    out = """
%(p)s_lookup:                            # r3 = a CRC no table before has
        lis r12, %(crc_h)d
        ori r12, r12, %(crc_l)d
        cmplw r3, r12
        bne %(p)sl_none
        li r3, %(base)d
        blr
""" % D + LT.replay(s['lk_none'], s['lk_none_word'], s['lk_none'] + 4, '%sl_none' % prefix) + """
%(p)s_size1:                             # r3 index -> r0 its size
        cmplwi r3, %(base)d
        bne %(p)ss1_orig
        li r0, %(size)d
        b 0x%(s1b)08X
""" % D + LT.replay(s['s1'], s['s1_word'], s['s1_back'], '%ss1_orig' % prefix) + """
%(p)s_size2:                             # r3 index -> r12 its size
        cmplwi r3, %(base)d
        bne %(p)ss2_orig
        li r12, %(size)d
        b 0x%(s2b)08X
""" % D + LT.replay(s['s2'], s['s2_word'], s['s2_back'], '%ss2_orig' % prefix) + """
%(p)s_fetch:                             # r7 index -> r0 its handler (r6 free)
        cmplwi r7, %(base)d
        bne %(p)sf_orig
        lis r6, %(hand_h)d
        ori r0, r6, %(hand_l)d
        b 0x%(fb)08X
""" % D
    if s['f_word'] >> 26 == 18:
        out += "%sf_orig:\n        b 0x%08X\n" % (prefix, LT.bdecode(s['f'], s['f_word']))
    else:
        out += "%sf_orig:\n        slwi r6, r7, 2\n        lwzx r0, r6, r29\n        b 0x%08X\n" % (prefix, s['f_back'])
    return out


def table_words(s, a, prefix):
    return {s['lk_none']: LT.branch(s['lk_none'], a.addr(prefix + '_lookup')),
            s['s1']: LT.branch(s['s1'], a.addr(prefix + '_size1')),
            s['s2']: LT.branch(s['s2'], a.addr(prefix + '_size2')),
            s['f']: LT.branch(s['f'], a.addr(prefix + '_fetch'))}


def chk(reg, fail, tmp='r0'):
    """branch to fail unless reg is a plausible heap pointer (0x10000000-0x8FFFFFFF, 4-aligned)"""
    return """
        addis %(t)s, %(r)s, -0x1000
        rlwinm. %(t)s, %(t)s, 0, 0, 0
        bne %(f)s
        andi. %(t)s, %(r)s, 3
        bne %(f)s""" % dict(t=tmp, r=reg, f=fail)


def mi_of(acc, out, fail, tmp='r0'):
    """out = the object's model instance [[acc + 0x3C] + 0xC] (acc checked), or branch to fail"""
    return chk(acc, fail, tmp) + """
        lwz %(o)s, 0x3C(%(a)s)""" % dict(o=out, a=acc) + chk(out, fail, tmp) + """
        lwz %(o)s, 0xC(%(o)s)""" % dict(o=out) + chk(out, fail, tmp)


_T = ('Whose: 0 this object (fighter or article), 1 the nearest opponent, 2 the last fighter this one hit, 3-10 '
      'player slots 1-8, 11 the last fighter that hit this one, 12 the fighter this attack hit (as the other '
      'Target commands).')
NEW_CMDS = [
    (CMD_NAME, 'h_outline', [
        ('Target', 0, _T),
        ('Red', 1, 'The glow\'s red, 0-255.'),
        ('Green', 1, 'Its green, 0-255.'),
        ('Blue', 1, 'Its blue, 0-255.'),
        ('Alpha', 1, 'Its strength: 255 = the colour at full at the very edge, higher up to 1020 (4x) for a harder '
                     'glow. 0 ends the outline (it fades out over this command\'s FadeOut; 0 at once).'),
        ('Tint', 1, 'A tint of the whole body toward the colour too, 0-255 (0: the edges only; 255: the body all '
                    'that colour). Edge-only glows use 0.'),
        ('Frames', 0, 'Held this many frames once faded in, then it fades out over FadeOut. 0: until Alpha 0, a KO '
                      'or the match end.'),
        ('FadeIn', 0, 'Frames to fade in (0: at once). A new outline on an object already glowing fades from where '
                      'that one is.'),
        ('FadeOut', 0, 'Frames to fade out when Frames run out (with Alpha 0: over this many; 0 at once).'),
        ('Flash', 0, 'A pulse: one cycle every Flash frames (full, off, full again, smoothly); 0 steady.')],
     'A coloured glow on an object\'s silhouette edges (a rim light), optionally with a body tint, faded in and out '
     'and pulsing: the fighter shaders\' own fresnel rim, coloured per object. One per object; ends with Alpha 0, its '
     'Frames, a KO, the match end or a training reset. New command: needs the patched cross_f.rpx '
     '(tools/outline_cave.py, exe_v46z_outline).'),
]


def find(orig):
    s = table_find(orig, CAVE, LIMIT)
    for at in FB_A + FB_B:
        assert orig(at) == 0x4E800421, 'FB1 unlock 0x%08X: 0x%08X (want bctrl)' % (at, orig(at))
    for at, want in FB_SIG.items():
        assert orig(at) == want, '0x%08X: 0x%08X, not 0x%08X' % (at, orig(at), want)
    for vt, fn in FB_BUILDERS.items():
        assert orig(vt) == fn, 'MI vtable 0x%08X: 0x%08X, not 0x%08X' % (vt, orig(vt), fn)
    for i, want in enumerate(NC_TARGET_SIG):
        assert orig(NC_TARGET + 4 * i) == want, 'nc_target 0x%08X' % (NC_TARGET + 4 * i)
    s['tick_prev'] = tick_prev(orig)
    assert not CAVE <= s['tick_prev'] < LIMIT, 'already patched (tick)'
    s['clear_at'] = clear_tail(orig)
    assert not CAVE <= s['clear_at'] < LIMIT, 'already patched (clear)'
    return s


DIAG_FMTS = [
    ('s_oc', 'S4OC tgt=%d acc=%08X mi=%08X rgb=%08X %08X %08X a=%08X\n'),
    ('s_od', 'S4OD tint=%08X fr=%d in=%d out=%d flash=%d k=%d ph=%d\n'),
    ('s_ot', 'S4OT n=%d k=%d acc=%08X ph=%d w=%08X eff=%08X left=%d\n'),
    ('s_of', 'S4OF n=%d mi=%08X off=%08X %08X %08X blink=%08X %08X\n'),
]


def _words(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ''.join('        .word 0x%08X\n' % struct.unpack_from('>I', b, i)[0] for i in range(0, len(b), 4))


def src(s, hand, diag=False, pad=False):
    D = dict(size=1 + NPARAMS, step=4 * (1 + NPARAMS), n=N_ENT, ent=ENT, nct=NC_TARGET,
             tick_prev=s['tick_prev'], clear_to=CLEAR_BACK, smvt_h=FIGHTER_SM_VT >> 16, smvt_l=FIGHTER_SM_VT & 0xFFFF,
             dead=DEAD, blink=BLINK, fo=FRES_OFF, fo4=FRES_OFF + 4, fo8=FRES_OFF + 8, b4=BLINK + 4,
             b8=BLINK + 8, b12=BLINK + 12, every=DIAG_EVERY, last=(N_ENT - 1) * ENT)
    out = table_src(s, 'ol', OL_INDEX, CMD_CRC, 1 + NPARAMS, hand)
    out += """
# --- Outline_Set(Target, Red, Green, Blue, Alpha, Tint, Frames, FadeIn, FadeOut, Flash):
#     (r3 accessor, r5 script state, r6 (+8 execute), r7 parameters) ---------------------------------------------
# entry (0x%(ent)X): +0 accessor (0 free), +4 instance, +8 phase (1 in, 2 held, 3 out), +0xC w, +0x10 in rate,
# +0x14 out rate, +0x18 Frames left, +0x1C-+0x24 colour x strength, +0x28-+0x30 colour, +0x34 tint, +0x38 Flash,
# +0x3C frames since the command, +0x40 the weight drawn (w x the pulse)
h_outline:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r5
        mr r30, r7
        mr r29, r3
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq ol_step
        lis r12, ol_g@ha
        addi r12, r12, ol_g@l
        lwz r11, 0xC(r12)               # commands run
        addi r11, r11, 1
        stw r11, 0xC(r12)
        li r0, 0
        stw r0, 0x10(r12)               # (diag: frames since)
        mr r3, r29
        lwz r4, 0(r30)                  # Target
        bl 0x%(nct)08X
        mr. r28, r3
        beq ol_step""" % D + mi_of('r28', 'r27', 'ol_step') + """
        lis r26, ol_tab@ha              # r26: its entry, or a free one, or the round-robin one
        addi r26, r26, ol_tab@l
        li r11, %(n)d
        mr r10, r26
        li r9, 0
olf_loop:
        lwz r0, 0(r10)
        cmplw r0, r28
        beq olf_have
        cmpwi r9, 0
        bne olf_next
        cmpwi r0, 0
        bne olf_next
        mr r9, r10
olf_next:
        addi r10, r10, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne olf_loop
        lfs f1, 0x10(r30)               # not showing: Alpha 0 -> nothing
        lis r12, ol_k@ha
        lfs f0, ol_k@l(r12)
        fcmpu cr0, f1, f0
        ble ol_done
        mr r10, r9
        cmpwi r10, 0
        bne olf_new
        lis r12, ol_g@ha                # all in use: the round-robin one
        addi r12, r12, ol_g@l
        lwz r11, 0x14(r12)
        addi r0, r11, 1
        cmplwi r0, %(n)d
        blt olf_rr
        li r0, 0
olf_rr:
        stw r0, 0x14(r12)
        mulli r11, r11, %(ent)d
        add r10, r26, r11
olf_new:
        li r0, 0                        # a new entry: from nothing
        stw r0, 8(r10)
        stw r0, 0xC(r10)
olf_have:
        mr r26, r10
        lis r12, ol_k@ha
        addi r12, r12, ol_k@l
        lfs f0, 0(r12)                  # 0
        lfs f1, 0x10(r30)               # Alpha
        fcmpu cr0, f1, f0
        bgt ol_start
        lwz r0, 8(r26)                  # Alpha 0: fade out (or off)
        cmpwi r0, 0
        beq ol_free
        lwz r3, 0x20(r30)               # FadeOut
        bl ol_rate
        stfs f1, 0x14(r26)
        lis r12, ol_k@ha
        lfs f0, ol_k@l(r12)
        fcmpu cr0, f1, f0
        beq ol_free
        li r0, 3
        stw r0, 8(r26)
        b ol_done
ol_free:
        li r0, 0
        stw r0, 0(r26)
        stw r0, 8(r26)
        b ol_done
ol_start:
        stw r28, 0(r26)
        stw r27, 4(r26)
        lfs f2, 0x10(r12)               # 1 / 255
        fmuls f3, f1, f2                # strength
        lfs f4, 4(r30)
        fmuls f4, f4, f2
        stfs f4, 0x28(r26)
        fmuls f4, f4, f3
        stfs f4, 0x1C(r26)
        lfs f4, 8(r30)
        fmuls f4, f4, f2
        stfs f4, 0x2C(r26)
        fmuls f4, f4, f3
        stfs f4, 0x20(r26)
        lfs f4, 0xC(r30)
        fmuls f4, f4, f2
        stfs f4, 0x30(r26)
        fmuls f4, f4, f3
        stfs f4, 0x24(r26)
        lfs f4, 0x14(r30)               # Tint (0-1)
        fmuls f4, f4, f2
        fcmpu cr0, f4, f0
        bge olt_lo
        fmr f4, f0
olt_lo:
        lfs f5, 4(r12)                  # 1
        fcmpu cr0, f4, f5
        ble olt_hi
        fmr f4, f5
olt_hi:
        stfs f4, 0x34(r26)
        lwz r0, 0x18(r30)               # Frames (negative: 0)
        cmpwi r0, 0
        bge ol_fr
        li r0, 0
ol_fr:
        stw r0, 0x18(r26)
        lwz r0, 0x24(r30)               # Flash (negative: 0)
        cmpwi r0, 0
        bge ol_fl
        li r0, 0
ol_fl:
        stw r0, 0x38(r26)
        li r0, 0
        stw r0, 0x3C(r26)
        lwz r3, 0x20(r30)               # FadeOut
        bl ol_rate
        stfs f1, 0x14(r26)
        lwz r3, 0x1C(r30)               # FadeIn
        bl ol_rate
        lis r12, ol_k@ha
        addi r12, r12, ol_k@l
        lfs f0, 0(r12)
        fcmpu cr0, f1, f0
        beq ol_now
        stfs f1, 0x10(r26)
        li r0, 1
        stw r0, 8(r26)
        b ol_eff
ol_now:
        lfs f1, 4(r12)                  # FadeIn 0: full at once
        stfs f1, 0xC(r26)
        li r0, 2
        stw r0, 8(r26)
ol_eff:
        lfs f1, 0xC(r26)                # drawn from this frame: w (the pulse starts full)
        stfs f1, 0x40(r26)
ol_done:
        bl ol_count
        mr r3, r30
        mr r4, r28
        mr r5, r27
        mr r6, r26
        bl ol_dcmd                      # (diag build: S4OC / S4OD; else a blr)
ol_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne ol_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
ol_ret:
        lmw r26, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# ol_rate(r3 frames) -> f1 1 / frames (frames > 0), else 0. r0 r12 f0
ol_rate:
        lis r12, ol_k@ha
        addi r12, r12, ol_k@l
        lfs f1, 0(r12)
        cmpwi r3, 0
        blelr
        stwu r1, -0x20(r1)
        xoris r3, r3, 0x8000
        stw r3, 0xC(r1)
        lis r0, 0x4330
        stw r0, 8(r1)
        lfd f1, 8(r1)
        lfd f0, 0x18(r12)               # 2^52 + 2^31
        fsub f1, f1, f0
        frsp f1, f1
        lfs f0, 4(r12)
        fdivs f1, f0, f1
        addi r1, r1, 0x20
        blr

# ol_count: ol_g +0 = entries in use. r0 r9-r12
ol_count:
        lis r12, ol_tab@ha
        addi r12, r12, ol_tab@l
        li r11, %(n)d
        li r9, 0
olc_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq olc_next
        addi r9, r9, 1
olc_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne olc_loop
        lis r12, ol_g@ha
        stw r9, ol_g@l(r12)
        blr

# --- ol_tick: bl from 0x032EFB78 (the effect manager's frame, r3 the screen-effect manager): the earlier tick, then the
#     outlines' frame ---------------------------------------------------------------------------------------------
ol_tick:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        bl 0x%(tick_prev)08X
        bl ol_frame
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

ol_frame:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x20(r1)
        lis r12, ol_g@ha
        addi r12, r12, ol_g@l
        lwz r11, 4(r12)                 # frames ticked
        addi r11, r11, 1
        stw r11, 4(r12)
        lwz r11, 0x10(r12)              # (diag) since the last command
        addi r11, r11, 1
        stw r11, 0x10(r12)
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq olr_out
        lis r31, ol_tab@ha
        addi r31, r31, ol_tab@l
        li r30, %(n)d
olr_loop:
        lwz r29, 0(r31)
        cmpwi r29, 0
        beq olr_next""" % D + mi_of('r29', 'r28', 'olr_drop') + """
        lwz r0, 4(r31)                  # the object's model changed: drop it
        cmplw r0, r28
        bne olr_drop
        lwz r12, 0x20(r29)              # a fighter KO'd (StatusModule +0x48 = 0x%(dead)X): drop it""" % D + \
        chk('r12', 'olr_live') + """
        lwz r11, 0(r12)
        lis r10, %(smvt_h)d
        ori r10, r10, %(smvt_l)d
        cmplw r11, r10
        bne olr_live
        lwz r11, 0x48(r12)
        cmpwi r11, %(dead)d
        beq olr_drop
olr_live:
        lis r12, ol_k@ha
        addi r12, r12, ol_k@l
        lfs f0, 0(r12)                  # 0
        lfs f2, 4(r12)                  # 1
        lfs f1, 0xC(r31)                # w
        lwz r0, 8(r31)
        cmpwi r0, 1
        bne olr_held
        lfs f3, 0x10(r31)               # fading in
        fadds f1, f1, f3
        fcmpu cr0, f1, f2
        blt olr_w
        fmr f1, f2
        li r0, 2
        stw r0, 8(r31)
        b olr_w
olr_held:
        cmpwi r0, 2
        bne olr_out3
        lwz r11, 0x18(r31)              # Frames left (0: no count)
        cmpwi r11, 0
        beq olr_w
        addi r11, r11, -1
        cmpwi r11, 0
        stw r11, 0x18(r31)
        bne olr_w
        lfs f3, 0x14(r31)               # Frames over: fade out, or off at once
        fcmpu cr0, f3, f0
        beq olr_drop
        li r0, 3
        stw r0, 8(r31)
        b olr_w
olr_out3:
        cmpwi r0, 3
        bne olr_drop
        lfs f3, 0x14(r31)
        fsubs f1, f1, f3
        fcmpu cr0, f1, f0
        ble olr_drop
olr_w:
        stfs f1, 0xC(r31)
        lwz r11, 0x3C(r31)              # the pulse
        addi r11, r11, 1
        stw r11, 0x3C(r31)
        lwz r10, 0x38(r31)
        cmpwi r10, 0
        ble olr_eff
        divwu r9, r11, r10              # m = t mod Flash; p = m / Flash; tri = |2p - 1|; f = tri^2 (3 - 2 tri)
        mullw r9, r9, r10
        subf r9, r9, r11
        stw r9, 0x14(r1)
        stw r10, 0x1C(r1)
        lis r0, 0x4330
        stw r0, 0x10(r1)
        stw r0, 0x18(r1)
        lfd f4, 0x10(r1)
        lfd f5, 0x18(r1)
        lfd f6, 0x20(r12)               # 2^52
        fsub f4, f4, f6
        fsub f5, f5, f6
        frsp f4, f4
        frsp f5, f5
        fdivs f4, f4, f5                # p
        lfs f5, 8(r12)                  # 2
        fmuls f4, f4, f5
        fsubs f4, f4, f2
        fabs f4, f4                     # tri
        lfs f6, 0xC(r12)                # 3
        fnmsubs f6, f5, f4, f6          # 3 - 2 tri
        fmuls f6, f6, f4
        fmuls f6, f6, f4
        fmuls f1, f1, f6
olr_eff:
        stfs f1, 0x40(r31)
        mr r3, r31
        li r4, %(n)d
        subf r4, r30, r4
        bl ol_dtick                     # (diag: S4OT)
        b olr_next
olr_drop:
        li r0, 0
        stw r0, 0(r31)
        stw r0, 8(r31)
olr_next:
        addi r31, r31, %(ent)d
        addi r30, r30, -1
        cmpwi r30, 0
        bne olr_loop
        bl ol_count
olr_out:
        lmw r28, 0x20(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- ol_fbA / ol_fbB: the FB1 unlock's bctrl (r3 the buffer, ctr the unlock; the instance / the locked FB1 in r30 / r28
#     (class A) or r31 / r27 (class B)): the outline into FB1, then the unlock as the game called it -------------------
ol_fbA:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r3, 0x10(r1)
        .word 0x7C0902A6                # mfctr r0
        stw r0, 0x14(r1)
        mr r4, r30
        mr r5, r28
        b ol_fbgo
ol_fbB:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r3, 0x10(r1)
        .word 0x7C0902A6                # mfctr r0
        stw r0, 0x14(r1)
        mr r4, r31
        mr r5, r27
ol_fbgo:
        bl ol_apply
        lwz r0, 0x14(r1)
        mtctr r0
        lwz r3, 0x10(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        bctr

# ol_apply(r4 instance, r5 FB1): g_fresnelOffset += colour x strength x weight; the tint mixed into blinkColor
ol_apply:
        lis r12, ol_g@ha
        lwz r0, ol_g@l(r12)
        cmpwi r0, 0
        beqlr""" % D + chk('r5', 'ola_no') + """
        lis r12, ol_tab@ha
        addi r12, r12, ol_tab@l
        li r11, %(n)d
ola_find:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq ola_next
        lwz r0, 4(r12)
        cmplw r0, r4
        bne ola_next
        lwz r0, 8(r12)
        cmpwi r0, 0
        bne ola_have
ola_next:
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne ola_find
ola_no:
        blr
ola_have:
        lis r11, ol_k@ha
        addi r11, r11, ol_k@l
        lfs f0, 0(r11)                  # 0
        lfs f1, 0x40(r12)               # weight
        fcmpu cr0, f1, f0
        blelr
        lfs f2, 0x1C(r12)               # the rim: g_fresnelOffset += colour x strength x weight
        lfs f3, %(fo)d(r5)
        fmadds f3, f2, f1, f3
        stfs f3, %(fo)d(r5)
        lfs f2, 0x20(r12)
        lfs f3, %(fo4)d(r5)
        fmadds f3, f2, f1, f3
        stfs f3, %(fo4)d(r5)
        lfs f2, 0x24(r12)
        lfs f3, %(fo8)d(r5)
        fmadds f3, f2, f1, f3
        stfs f3, %(fo8)d(r5)
        lfs f2, 0x34(r12)               # the tint: t = tint x weight
        fmuls f2, f2, f1
        fcmpu cr0, f2, f0
        ble ola_done
        lfs f4, 4(r11)                  # 1
        lfs f5, %(b12)d(r5)        # a0
        fsubs f6, f4, f2                # 1 - t
        fmuls f7, f5, f6                # a0 (1 - t)
        fadds f8, f7, f2                # A = a0 (1 - t) + t
        fcmpu cr0, f8, f0
        ble ola_done
        fdivs f9, f4, f8                # 1 / A
        lfs f10, %(blink)d(r5)          # rgb = (rgb0 a0 (1 - t) + colour t) / A
        lfs f11, 0x28(r12)
        fmuls f11, f11, f2
        fmadds f10, f10, f7, f11
        fmuls f10, f10, f9
        stfs f10, %(blink)d(r5)
        lfs f10, %(b4)d(r5)
        lfs f11, 0x2C(r12)
        fmuls f11, f11, f2
        fmadds f10, f10, f7, f11
        fmuls f10, f10, f9
        stfs f10, %(b4)d(r5)
        lfs f10, %(b8)d(r5)
        lfs f11, 0x30(r12)
        fmuls f11, f11, f2
        fmadds f10, f10, f7, f11
        fmuls f10, f10, f9
        stfs f10, %(b8)d(r5)
        stfs f8, %(b12)d(r5)
ola_done:
        mr r3, r12
        b ol_dfb                        # (diag: S4OF; else a blr)

# --- ol_clear: the slow-motion clear-all chain (training reset, restart, match start / end; a leaf: r3 / r10 / LR
#     kept): every outline off, then on --------------------------------------------------------------------------
ol_clear:
        lis r12, ol_tab@ha
        addi r12, r12, ol_tab@l
        li r11, %(n)d
        li r0, 0
olx_loop:
        stw r0, 0(r12)
        stw r0, 8(r12)
        addi r12, r12, %(ent)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne olx_loop
        lis r12, ol_g@ha
        stw r0, ol_g@l(r12)
        b 0x%(clear_to)08X
""" % D
    if diag:
        out += _diag_src()
    else:
        out += """
ol_dcmd:
ol_dtick:
ol_dfb:
        blr
"""
    out += ("        .word 0\n" if pad else "") + """
ol_k:                                   # +0 0, +4 1, +8 2, +0xC 3, +0x10 1/255, +0x18 2^52 + 2^31, +0x20 2^52
        .float 0
        .float 1
        .float 2
        .float 3
        .float 0.00392156862745098
        .word 0
        .word 0x43300000
        .word 0x80000000
        .word 0x43300000
        .word 0
ol_g:                                   # +0 entries in use, +4 frames ticked, +8 FB1 writes, +0xC commands,
        .word 0                         # +0x10 frames since the last command (diag), +0x14 round robin
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
ol_tab:
""" + '        .word 0\n' * (N_ENT * ENT // 4) + (_diag_data() if diag else '')
    return out


def _diag_src():
    import diag_godfist_cave as G
    rep = """
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        .word 0x%08X
        bctrl""" % (G.OSREPORT_VENEER >> 16, G.OSREPORT_VENEER & 0xFFFF, G.CRCLR_CR1EQ)
    gate = """
        lis r12, ol_g@ha
        addi r12, r12, ol_g@l
        lwz r11, 0x10(r12)              # the first %(e)d frames after a command, then every %(e)dth
        cmpwi r11, %(e)d
        blt %(lab)s_log
        li r9, %(e)d
        divwu r8, r11, r9
        mullw r8, r8, r9
        cmpw r8, r11
        bne %(lab)s_out
%(lab)s_log:"""
    return """
# --- diag: S4OC / S4OD at every command (r3 parameters, r4 target accessor, r5 instance, r6 entry) -------------------
ol_dcmd:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x28(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        mr r28, r6
        lis r3, s_oc@ha
        addi r3, r3, s_oc@l
        lwz r4, 0(r31)
        mr r5, r30
        mr r6, r29
        lwz r7, 4(r31)
        lwz r8, 8(r31)
        lwz r9, 0xC(r31)
        lwz r10, 0x10(r31)""" + rep + """
        lis r3, s_od@ha
        addi r3, r3, s_od@l
        lwz r4, 0x14(r31)
        lwz r5, 0x18(r31)
        lwz r6, 0x1C(r31)
        lwz r7, 0x20(r31)
        lwz r8, 0x24(r31)
        lis r9, ol_tab@ha
        addi r9, r9, ol_tab@l
        subf r9, r9, r28
        li r0, %(ent)d
        divwu r9, r9, r0
        lwz r10, 8(r28)""" % dict(ent=ENT) + rep + """
        lmw r27, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# --- diag: S4OT per outline frame (r3 entry, r4 its number) ----------------------------------------------------------
ol_dtick:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x28(r1)
        mr r31, r3
        mr r30, r4""" + gate % dict(e=DIAG_EVERY, lab='odt') + """
        lis r3, s_ot@ha
        addi r3, r3, s_ot@l
        lis r12, ol_g@ha
        addi r12, r12, ol_g@l
        lwz r4, 4(r12)
        mr r5, r30
        lwz r6, 0(r31)
        lwz r7, 8(r31)
        lwz r8, 0xC(r31)
        lwz r9, 0x40(r31)
        lwz r10, 0x18(r31)""" + rep + """
odt_out:
        lmw r27, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# --- diag: S4OF at an FB1 write (r3 entry, r4 instance, r5 FB1) --------------------------------------------------
ol_dfb:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x28(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        lis r12, ol_g@ha
        addi r12, r12, ol_g@l
        lwz r11, 8(r12)                 # FB1 writes
        addi r11, r11, 1
        stw r11, 8(r12)""" + gate % dict(e=DIAG_EVERY, lab='odf') + """
        lis r3, s_of@ha
        addi r3, r3, s_of@l
        lis r12, ol_g@ha
        addi r12, r12, ol_g@l
        lwz r4, 8(r12)
        mr r5, r30
        lwz r6, %(fo)d(r29)
        lwz r7, %(fo4)d(r29)
        lwz r8, %(fo8)d(r29)
        lwz r9, %(b)d(r29)
        lwz r10, %(b12)d(r29)""" % dict(fo=FRES_OFF, fo4=FRES_OFF + 4, fo8=FRES_OFF + 8, b=BLINK, b12=BLINK + 12) + rep + """
odf_out:
        lmw r27, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
"""


def _diag_data():
    out = ''
    for lab, fmt in DIAG_FMTS:
        out += '%s:\n' % lab + _words(fmt)
    return out


def build(orig, diag=False):
    s = find(orig)
    hand, pad = 0, False
    for _p in range(3):
        a = Asm(CAVE)
        a.asm(src(s, hand, diag, pad))
        hand = a.addr('h_outline')
        if a.addr('ol_k') % 8:
            pad = not pad
    words = a.words()
    end = CAVE + 4 * len(words)
    assert end <= LIMIT, 'cave too big: 0x%08X' % end
    assert a.addr('ol_k') % 8 == 0, 'ol_k not 8-aligned (its doubles)'
    for x in range(CAVE, LIMIT, 4):
        assert orig(x) == 0, 'cave word 0x%08X not free' % x
    out = {CAVE + 4 * i: w for i, w in enumerate(words)}
    out.update(table_words(s, a, 'ol'))
    for at in FB_A:
        out[at] = LT.branch(at, a.addr('ol_fbA')) | 1
    for at in FB_B:
        out[at] = LT.branch(at, a.addr('ol_fbB')) | 1
    out[TICK_AT] = LT.branch(TICK_AT, a.addr('ol_tick')) | 1
    out[s['clear_at']] = LT.branch(s['clear_at'], a.addr('ol_clear'))
    return out, a.labels, s


def rpx_reader(path, cave=CAVE, limit=LIMIT):
    """the executable's words; the grown end (up to limit) reads 0"""
    import kind_expand as K
    img = K.Image(path)

    def orig(addr):
        try:
            return img.w(addr)
        except KeyError:
            if cave <= addr < limit:
                return 0
            raise
    return orig


def labels(path, cmds=None):
    """the commands' entries in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then puts them in Events.cfg
    and tools/acmd_info.json; their group, help and examples come from acmd_ext_help.py)"""
    import json
    from acmd_ext_help import GROUP, HELP, EXAMPLES
    d = json.load(open(path))
    for name, _h, params, desc in (cmds or NEW_CMDS):
        e = {'_command': name, '_new': True, '_name': name, '_size': 1 + len(params), '_desc': desc,
             '_format': [t for _n, t, _d in params]}
        for k, (pname, _t, pdesc) in enumerate(params):
            e[str(k)] = {'name': pname, 'desc': pdesc, 'confidence': 'high'}
        e['_example'] = EXAMPLES.get(name, [])
        e['_group'], e['_help'] = GROUP.get(name), HELP.get(name, [])
        d['%08X' % LT.crc(name)] = e
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def present(img_w, crc=CMD_CRC, cave=CAVE):
    """the executable has this cave (the command's CRC in its lookup) - for port_check"""
    hi, lo = 0x3D800000 | (crc >> 16), 0x618C0000 | (crc & 0xFFFF)
    try:
        return any(img_w(x) == hi and img_w(x + 4) == lo for x in range(cave, cave + 0x40, 4))
    except Exception:              # noqa: BLE001
        return False


def pulse(t, flash):
    """the pulse factor at frame t of an outline (Python reference)"""
    if flash <= 0:
        return 1.0
    tri = abs(2.0 * (t % flash) / flash - 1.0)
    return tri * tri * (3.0 - 2.0 * tri)


def apply_ref(fb, rgb255, alpha, tint255, weight):
    """the FB1 words the cave writes (Python reference): fb {'off': [r, g, b], 'blink': [r, g, b, a]} -> the same"""
    s = alpha / 255.0
    c = [x / 255.0 for x in rgb255]
    off = [o + ci * s * weight for o, ci in zip(fb['off'], c)]
    blink = list(fb['blink'])
    t = min(max(tint255 / 255.0, 0.0), 1.0) * weight
    if t > 0:
        a0 = blink[3]
        A = a0 * (1 - t) + t
        if A > 0:
            blink = [(b0 * a0 * (1 - t) + ci * t) / A for b0, ci in zip(blink[:3], c)] + [A]
    return {'off': off, 'blink': blink}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rpx', help='the executable to patch (exe_v46z_inv or later)')
    p.add_argument('--labels', help='update this param_labels.json with Outline_Set')
    p.add_argument('--diag', action='store_true', help='TEST ONLY: the OSReport build (S4OC / S4OD / S4OT / S4OF lines, '
                   'docs/native-notes.md "Outline")')
    args = p.parse_args()
    if args.labels:
        labels(args.labels)
        return
    if not args.rpx:
        p.error('--rpx or --labels')
    words, lab, _s = build(rpx_reader(args.rpx), args.diag)
    print(' '.join(['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] +
                   ['0x%08X=0x%08X' % kv for kv in sorted(words.items())]))
    sys.stderr.write('outline: %d words, Outline_Set index %d (0x%08X), h_outline 0x%08X, ol_apply 0x%08X, '
                     'end 0x%08X\n' % (len(words), OL_INDEX, CMD_CRC, lab['h_outline'], lab['ol_apply'],
                                       max(a for a in words if a >= CAVE) + 4))


if __name__ == '__main__':
    main()
