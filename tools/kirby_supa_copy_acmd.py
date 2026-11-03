#!/usr/bin/env python3
"""Kirby's Supamario copy (Supamario fix 90): his Mario-copy throw's effect and sound scripts (MarioSpecialN /
MarioSpecialAirN, Kirby's motions 0x331 / 0x332) for the Kamehameha too.

  python3 tools/kirby_supa_copy_acmd.py KIRBY_BODY_DIR OUT_DIR

KIRBY_BODY_DIR: Kirby's script/animcmd/body folder (effect.bin, sound.bin). Writes OUT_DIR/effect.bin and
sound.bin. With a Supamario copy, Kirby's int 0x100000A0 is 1 (fighters/kirby/kirby.c, "Supamario copy"): each
of the scripts' commands (but frames and the start's dust) then runs only while it's 0 (Int_Var_Compare /
True, as tools/kirby_throwb_acmd.py's tiers), so the fireball's flash (Mario's effect 0x3030001: Mario's
files, which a Supamario-only match doesn't load), red overlay, light and throw sound stay off; and while it's
1 Supamario's own SpecialN effect script's release plays (tools/supamario_kame_build.py special_scripts: its
charge effects ended at frame 13, the release parts at frame 14) on Kirby's hand, bone 0x10 (Mario's 0x11:
the copy flash's), turned (0, 0, 139.8) as kirby.c's skame_fx (Kirby's 0x10 frame vs Mario's 0x11).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402

MARKER = 0x100000A0
IVC = acmd.BY_NAME['int_var_compare']
TRUE = acmd.BY_NAME['true']
FRAME = acmd.BY_NAME['frame']
END = acmd.END
JUMP = acmd.BY_NAME['jump']
KEEP = (FRAME, END, JUMP, acmd.BY_NAME['graphic_effect2'])   # the start's dust (common 0x100000C) stays
HAND, HAND_ROT = 0x10, (0.0, 0.0, 139.8)
CHARGE_FX = (0x03410019, 0x0341001A, 0x0341001F)            # PtcSupamarioKmhCrg / CrgON / tsubu
RELEASE_FX = ((0x03410020, 1.0), (0x0341001D, 0.8))         # Supamario's SpecialN effect script, frame 14
SCRIPTS = ('mariospecialn', 'mariospecialairn')


def when(value, c):
    return [acmd.Command(IVC, [MARKER, 0, value]), acmd.Command(TRUE, [2 + c.info['size']]), c]


def at_frame(cmds, frame):
    """the commands' index at FRAME frame (the first command after it), adding the FRAME if it isn't there"""
    t = 0.0
    for i, c in enumerate(cmds):
        if c.ident == FRAME:
            if c.params[0] == frame:
                return i + 1
            if c.params[0] > frame:
                cmds.insert(i, acmd.Command(FRAME, [frame]))
                return i + 1
            t = c.params[0]
        elif c.ident == END:
            cmds.insert(i, acmd.Command(FRAME, [frame]))
            return i + 1
    assert t < frame
    cmds.append(acmd.Command(FRAME, [frame]))
    return len(cmds)


def effect_script(cmds):
    out = []
    for c in cmds:
        out += [c] if c.ident in KEEP else when(0, c)
    i = at_frame(out, 13.0)
    kill = []
    for e in CHARGE_FX:
        kill += when(1, acmd.Command(acmd.BY_NAME['terminate_graphic_effect'], [e, 1, 1]))
    out[i:i] = kill
    i = at_frame(out, 14.0)
    rel = []
    for e, size in RELEASE_FX:
        rel += when(1, acmd.Command(acmd.BY_NAME['external_graphic'], [e, HAND, 0.0, 0.0, 0.0, *HAND_ROT, size, 0]))
    out[i:i] = rel
    return out


def sound_script(cmds):
    out = []
    for c in cmds:
        out += [c] if c.ident in KEEP else when(0, c)
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1:]
    os.makedirs(out, exist_ok=True)
    for f, fn in (('effect.bin', effect_script), ('sound.bin', sound_script)):
        a = acmd.ACMDFile.load(os.path.join(src, f))
        for n in SCRIPTS:
            s = a.scripts.get(acmd.crc(n))
            if s is None or any(c.ident == JUMP for c in s):
                continue                    # a JUMP to the ground one: done there
            a.scripts[acmd.crc(n)] = fn(list(s))
            print('%s %s: %d -> %d commands' % (f, n, len(s), len(a.scripts[acmd.crc(n)])))
        a.save(os.path.join(out, f))


if __name__ == '__main__':
    main()
