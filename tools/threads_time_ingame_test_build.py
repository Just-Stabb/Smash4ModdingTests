#!/usr/bin/env python3
"""In-game test v3 of ACMD threads (exe_v46m) and the time commands (exe_v46n, ticked by exe_v46u_threads) on
Supamario's taunts, with the diag executable exe_v46u_threads_diag (tools/diag_godfist_cave.py + diag_threads_cave.py +
diag_taunt_time_cave.py + diag_tick_cave.py on exe_v46u_threads). v3: the markers are Graphic_Effect2 (v2's
Graphic_Effect is the one effect command the EffectModule's gate, vt +0x32C, can refuse: none showed in v2); the
thread draws both kinds every 10 frames (S4GE logs the gate); the side taunt left speeds up (Time_Scale 2).
v1's tests (tools/thread_ingame_test_build.py, tools/time_stage_ingame_test_build.py) logged nothing from the up
taunt's game script in game, so v2 first proves the taunt's scripts run: every taunt, both facings, starts in its
GAME script with a log line, a big star over his head and a weak hitbox, and in its EFFECT script with a log line and
a hit flash in front of him; then the taunt's own test.

  python3 tools/threads_time_ingame_test_build.py GAME.bin EFFECT.bin OUT_GAME.bin OUT_EFFECT.bin

The game scripts (R and L alike; V = 1 up R, 2 up L, 3 side R, 4 side L, 5 down R, 6 down L):

    SET_FLOAT(Value=V, Variable=0x0F0003F7)       // S4GF k=7 v=V: the game script ran
    Graphic_Effect2(0x100000F, Bone=0, Y=20, Size=1.2)  // a big star over his head
    Hitbox(ID=0, Bone=0, Damage=1, Angle=361, KBG=10, BKB=30, Size=9, Y=8, ...)   // a weak hit on anyone near
    up:   Thread_Start(ID=0x7E){ 60 frames: SET_FLOAT(1, 0x0F0003F8) (k=8 each frame); every 10 frames a small star
                                 (Graphic_Effect2, Y=18) and a tiny one (Graphic_Effect, Y=26: the gate's evidence);
                                 SET_FLOAT(60, 0x0F0003F9) (k=9 at its end) }
    side: R Time_Scale(Rate=0.5, Frames=120) / L Time_Scale(Rate=2, Frames=120); SET_FLOAT(Value=rate, 0x0F0003FA)
    down: Stage_Freeze(On=1, Frames=180); Target_Time_Scale(Target=1, Rate=0.5, Frames=180);
          SET_FLOAT(Value=1, Variable=0x0F0003FB)                                         // k=11
    WAIT(Frames=4)
    Remove_All_Hitboxes()

The effect scripts: SET_FLOAT(Value=V, Variable=0x0F0003F6) (k=6) and Graphic_Effect2(0x1000002 hit flash, Bone=0,
Y=8, Z=8, Size=0.8) put before the taunt's own effect script (which then plays as before; a taunt with no effect
script gets just these). The writes to 0x0F0003F0 + k print only with the diag executable.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import thread_ingame_test_build as TH  # noqa: E402

DIAG = 0x0F0003F0
STAR = 0x100000F                # common "Large star"
FLASH = 0x1000002               # common heavy hit flash
TAUNTS = [('appealhir', 1, 'up'), ('appealhil', 2, 'up'), ('appealsr', 3, 'side'), ('appealsl', 4, 'side'),
          ('appeallwr', 5, 'down'), ('appeallwl', 6, 'down')]


def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def proof(v):
    return [cmd('set_float', float(v), DIAG + 7),
            cmd('graphic_effect2', STAR, 0, 0.0, 20.0, 0.0, 0.0, 0.0, 0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
            cmd('hitbox', 0, 0, 0, 1.0, 361, 10, 0, 30, 9.0, 0.0, 8.0, 0.0, 0, 0.0, 1.0, 1.0, 1, 1, 0, 0, 1, 3, 1, 4)]


def game_script(v, kind):
    body = proof(v)
    if kind == 'up':
        body += thread_block()
    elif kind == 'side':
        rate = 0.5 if v % 2 else 2.0
        body += [cmd('time_scale', rate, 120), cmd('set_float', rate, DIAG + 10)]
    else:
        body += [cmd('stage_freeze', 1, 180), cmd('target_time_scale', 1, 0.5, 180), cmd('set_float', 1.0, DIAG + 11)]
    body += [cmd('wait', 4.0), cmd('remove_all_hitboxes'), acmd.Command(acmd.END)]
    return body


def stars():
    return [cmd('graphic_effect2', STAR, 0, 0.0, 18.0, 0.0, 0.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0),
            cmd('graphic_effect', STAR, 0, 0.0, 26.0, 0.0, 0.0, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)]


def thread_block(frames=60):
    """Thread_Start(ID 0x7E){ frames x (k=8, WAIT 1), the stars on every 10th, k=9 v=frames at its end }"""
    body = []
    for i in range(frames):
        body += [cmd('set_float', 1.0, DIAG + 8)] + (stars() if i % 10 == 0 else []) + [cmd('wait', 1.0)]
    body += [cmd('set_float', float(frames), DIAG + 9)]
    return [cmd('thread_start', 4 + TH.size(body) + 1, TH.TID, 0)] + body + [acmd.Command(acmd.END)]


def effect_lead(v):
    return [cmd('set_float', float(v), DIAG + 6),
            cmd('graphic_effect2', FLASH, 0, 0.0, 8.0, 8.0, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)]


def main():
    a = sys.argv[1:]
    if len(a) != 4:
        sys.exit(__doc__)
    g = acmd.ACMDFile.load(a[0])
    e = acmd.ACMDFile.load(a[1])
    for n, v, kind in TAUNTS:
        assert g.script(n) is None, '%s already has a game script: refusing to replace it' % n
        g.scripts[acmd.crc(n)] = game_script(v, kind)
        own = e.script(n) or [acmd.Command(acmd.END)]
        e.scripts[acmd.crc(n)] = effect_lead(v) + own
    g.save(a[2])
    e.save(a[3])
    g2, e2 = acmd.ACMDFile.load(a[2]), acmd.ACMDFile.load(a[3])
    for n, v, kind in TAUNTS:
        assert [c.encode() for c in g2.script(n)] == [c.encode() for c in game_script(v, kind)], n
        assert [c.encode() for c in e2.script(n)][:2] == [c.encode() for c in effect_lead(v)], n
    for k in set(g.scripts) - {acmd.crc(n) for n, _v, _k in TAUNTS}:
        assert [c.encode() for c in g2.scripts[k]] == [c.encode() for c in g.scripts[k]]
    print('wrote %s and %s' % (a[2], a[3]))
    for n, v, kind in TAUNTS[::2]:
        print('--- %s (game)' % n)
        print(acmd.fmt_script(g2.script(n))[:900])
        print('--- %s (effect)' % n)
        print(acmd.fmt_script(e2.script(n))[:600])


if __name__ == '__main__':
    main()
