#!/usr/bin/env python3
"""Squirtle's moves (fighters/pzenigame/README.md): his scripts, MSC, the water article and his stats.

  python3 tools/pzenigame_build.py DUMP ULT BODY VL MODEL MARIO OUT [--param FIGHTER_PARAM] [--bank DIR]

DUMP: the smashline dump's lua2cpp_pzenigame (pzenigame/, pzenigame_water/); ULT: Ultimate's
fighter/pzenigame (motion/body/c00/motion_list.bin, model/body/c00/model.nusktb); BODY: his folder's
script/animcmd/body (Mario's, universal-mechanics game.bin); VL: his fighter_param_vl_pzenigame.bin
(Mario's copy); MODEL: his converted model/body/c00 (the ACMD joint ids); MARIO: Mario's fighter folder
(model/fireball, motion/fireball: the water's stand-ins). Writes OUT/:
- fighter/pzenigame/script/animcmd/body/: tools/ultimate_acmd.py, his normals and (with
  fighters/pzenigame/specials_acmd.json) his specials in Mario's special slots, their effects
  (fighters/pzenigame/pzenigame_effects.json: tools/vfxb_to_ptcl.py's ids); param/fighter/
  fighter_param_vl_pzenigame.bin (cancel / intangible frames);
- fighter/pzenigame/script/msc/pzenigame.mscsb from fighters/pzenigame/pzenigame.c (PZ_* below);
- the water (article 5, weapon kind 0x198: extra_kinds.json "weapons"): script/msc/water/water.mscsb from
  fighters/pzenigame/weapons/water.c (WATER_* below), script/animcmd/weapon/water/ (Ultimate's
  pzenigame_water Regular, one motion per charge level: WATER_LEVELS), model/water/c00 (Mario's
  fireball model, hidden: nud.hidden) and motion/water/main.pac (the fireball's);
- --param: param/fighter/fighter_param.bin with his stats (STATS: Ultimate's fighter_param.prc, as
  Hero's / Steve's);
- --bank: effect/pzenigame/pzenigame.010d0000.{ptcl,efc} from DIR (tools/vfxb_to_ptcl.py's output);
- --sound DIR: tools/ultimate_sound.py's output (his Ultimate se / voice banks, cheer, sequences, the label
  table, sound_ids.json; the base's rows kept, so no ids move): the body's sound and expression scripts
  translated from Ultimate's (tools/ultimate_acmd.py --sound-ids / --expressions), fighter/pzenigame/sound/
  and sound/config/soundlabeltable.bin written.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import nud  # noqa: E402
import ultimate_acmd as U  # noqa: E402

KIND = 0x46
# pzenigame.c's specials. Ultimate's numbers where its data has them (vl.prc param_special_n
# charge_frame; SpecialNShot's six waters 4 frames apart from frame 7); Withdraw's speeds are in
# Ultimate's status code, not its data: approximations (README)
CONSTS = dict(PZ_WATER_ARTICLE='0x5', PZ_N_CHARGE_MAX='45', PZ_N_SHOTS='6', PZ_N_SHOT_FRAME='7.0f',
              PZ_N_SHOT_EVERY='4.0f', PZ_S_SPEED_START='1.2f', PZ_S_SPEED_MAX='2.4f', PZ_S_ACCEL='10',
              PZ_S_SLIDE='40', PZ_S_BRAKE='0.9f', PZ_S_BOUNCE='1.0f',
              # Water Gun's aim: Ultimate's SHOOT_ANGLE_ENABLE frames (SpecialNShot 5 - 40) and
              # param_special_n angle_up 40 / angle_down 25 / angle_speed 2; the stick's dead zone mine
              PZ_N_AIM_START='5.0f', PZ_N_AIM_END='40.0f', PZ_N_AIM_UP='40.0f', PZ_N_AIM_DOWN='25.0f',
              PZ_N_AIM_SPEED='2.0f', PZ_N_AIM_DEAD='0.2f',
              # the water: Ultimate's param_water (vl.prc)
              WATER_SPEED_MIN='2.0f', WATER_SPEED_ADD='2.2f', WATER_CHARGE_MAX='45', WATER_LIFE='20',
              WATER_ACCEL_Y='0.01f', WATER_FALL_MAX='1.2f',
              # the mouth from the hand the game places it at (his SpecialNShot pose, frames 7 - 27:
              # mouth ~(forward 9.5, up 5), left hand ~(8.0, 2.2))
              WATER_MOUTH_FWD='1.5f', WATER_MOUTH_UP='2.8f')
PZDIR = os.path.join(ROOT, 'fighters', 'pzenigame')
# the water's motions: charge level 0 / 1 / 2 (water.c water_level: thirds of the charge) at the charge
# ratio 0 / 0.5 / 1: Ultimate's reaction_add 75 x it on the push's knockback (fixed 40), its
# scale_min 0.8 - scale_max 1.5 on the push and the effect; the fireball's motion info has 4 slots
WATER_LEVELS = (0.0, 0.5, 1.0)
WATER_SLOTS = ('water0', 'water1', 'water2', 'waternone')
# fighter_param (kind 0x46; were Mario's): Ultimate's fighter_param.prc, Hero's / Steve's mapping (walk
# accel mul / add / max, ground brake x 0.45, dash, run accel mul / add / max, jump squat, jump x / mul /
# max / aerial mul, jump / mini jump heights x 0.82 / x 0.9 and the aerial jump as it is, air accel mul /
# add / max / brake, gravity, fall / fast fall, landing lag n / f / b / hi / lw, weight, jumps)
STATS = ('1=0.1575 2=0.1575 3=1.281 7=0.0396 8=1.936 9=0.088 10=0.044 11=1.76 12=3 13=0.95 14=0.9 15=1.3 '
         '16=1 17=28.99 18=15.33 19=35.35 20=0.095 21=0.01 22=1.01 23=0.018 24=0.128 25=1.35 27=2.16 '
         '28=8 29=6 30=18 31=6 32=16 33=75 34=2').split()


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def compile_msc(src, out_path):
    """src with CONSTS put in, compiled"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = open(src).read()
    for k in sorted(CONSTS, key=len, reverse=True):
        text = text.replace(k, CONSTS[k])
    with tempfile.NamedTemporaryFile('w', suffix='.c', delete=False) as f:
        f.write(text)
    try:
        run(os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'), f.name, '-o', out_path)
    finally:
        os.unlink(f.name)
    assert os.path.getsize(out_path) > 0


def ids():
    out = {}
    for path in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(PZDIR, 'pzenigame_effects.json')):
        out.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
    return out


def body_scripts(a, fighter, param):
    out = os.path.join(fighter, 'script/animcmd/body')
    os.makedirs(out, exist_ok=True)
    os.makedirs(param, exist_ok=True)
    return run(os.path.join(HERE, 'ultimate_acmd.py'), os.path.join(a.dump, 'pzenigame'),
               os.path.join(a.body, 'game.bin'), os.path.join(out, 'game.bin'), a.model,
               '--others', a.body, out,
               '--motion-list', os.path.join(a.ult, 'motion/body/c00/motion_list.bin'),
               '--mtable', os.path.join(a.body, 'motion.mtable'), os.path.join(out, 'motion.mtable'),
               '--vl', a.vl, os.path.join(param, 'fighter_param_vl_pzenigame.bin'), '--vl-kind', 'mario',
               '--effects', os.path.join(ROOT, 'reference/ultimate_sys_effects.json') + ',' +
               os.path.join(PZDIR, 'pzenigame_effects.json'), os.path.join(a.ult, 'model/body/c00/model.nusktb'),
               '--translate', os.path.join(PZDIR, 'specials_acmd.json'),
               *(['--sound-ids', os.path.join(a.sound, 'sound_ids.json'), '--expressions'] if a.sound else []))


# the special slots his moves use (pzenigame.c): Mario's scripts there go. Ultimate's start motions have no
# game script (SpecialNStart, SpecialSStart: nothing to translate), so Mario's fireball / cape (articles 0 /
# 1, the cape's reflector) stayed; the ground Withdraw hit (0x21C) plays the air one's (one Ultimate file)
SPECIAL_SLOTS = (0x211, 0x212, 0x213, 0x215, 0x216, 0x217, 0x219, 0x21A, 0x21B, 0x21C, 0x21D, 0x21E, 0x21F,
                 0x220, 0x221, 0x225, 0x229, 0x22D, 0x239, 0x23D)
EMPTY_GAME = (0x211, 0x215, 0x219, 0x21D)
SAME_AS = {0x21C: 0x220}


def special_slots(fighter, body):
    import struct
    d = os.path.join(fighter, 'script/animcmd/body')
    mt = open(os.path.join(d, 'motion.mtable'), 'rb').read()
    h = [struct.unpack_from('>I', mt, 4 * i)[0] for i in range(len(mt) // 4)]
    end = [acmd.Command(acmd.END)]
    for fn in ('game', 'effect', 'sound'):
        f = acmd.ACMDFile.load(os.path.join(d, fn + '.bin'))
        for dst, src in SAME_AS.items():
            f.scripts[h[dst]] = [acmd.Command(c.ident, list(c.params)) for c in f.scripts.get(h[src], end)]
        if fn == 'game':
            for i in EMPTY_GAME:
                f.scripts[h[i]] = list(end)
        if fn == 'sound':            # Mario's left there (the fireball's, the cape's, his voice): gone
            base = acmd.ACMDFile.load(os.path.join(body, 'sound.bin')).scripts
            for i in SPECIAL_SLOTS:
                if h[i] not in f.scripts or (h[i] in base and [str(c) for c in f.scripts[h[i]]] == [str(c) for c in base[h[i]]]):
                    f.scripts[h[i]] = list(end)
        f.save(os.path.join(d, fn + '.bin'))
    return 'specials: game emptied %s, %s' % (', '.join('0x%X' % i for i in EMPTY_GAME),
                                              ', '.join('0x%X = 0x%X' % kv for kv in SAME_AS.items()))


def water_scripts(a, fighter):
    """the water's game / effect scripts, one motion per WATER_LEVELS (its MSC picks by the charge)"""
    U.EFFECT_CONDS = (U.LR_LEFT,)
    fns = U.functions(open(os.path.join(a.dump, 'pzenigame_water/Regular.txt')).read())
    game, effect = {}, {}
    for lv, k in enumerate(WATER_LEVELS):
        scale = 0.8 + 0.7 * k
        gtr, etr = U.Translator({}), U.EffectTranslator({}, ids(), {})
        g = gtr.script(fns['game_regular'])
        for c in g:
            if c.name in ('Special_Hitbox', 'Extended_Special_Hitbox'):
                c.params[6] = int(round(40 + 75 * k))          # fixed knockback (the push): + reaction_add
                c.params[8] = round(c.params[8] * scale, 2)     # its size
        e = etr.script(fns['effect_regular'])
        for c in e:
            if c.name.startswith(('External_Graphic', 'Graphic_Effect')):
                c.params[8] = round(c.params[8] * scale, 3)
        assert not etr.missing, etr.missing
        game[WATER_SLOTS[lv]], effect[WATER_SLOTS[lv]] = g, e
    U.EFFECT_CONDS = ()
    wdir = os.path.join(fighter, 'script/animcmd/weapon/water')
    os.makedirs(wdir, exist_ok=True)
    end = [acmd.Command(acmd.END)]
    for fn, sc in (('game', game), ('effect', effect), ('sound', {})):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, end) for n in WATER_SLOTS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in WATER_SLOTS))
    # Mario's fireball model, drawing nothing, and its motion: the fireball descriptor's, which the copy keeps
    mdir = os.path.join(fighter, 'model/water/c00')
    shutil.copytree(os.path.join(a.mario, 'model/fireball/c00'), mdir, dirs_exist_ok=True)
    hidden = nud.hidden(os.path.join(mdir, 'model.nud'))
    open(os.path.join(mdir, 'model.nud'), 'wb').write(hidden)
    os.makedirs(os.path.join(fighter, 'motion/water'), exist_ok=True)
    shutil.copy(os.path.join(a.mario, 'motion/fireball/main.pac'), os.path.join(fighter, 'motion/water/main.pac'))
    return 'water: %s; game %s' % (', '.join(WATER_SLOTS[:len(WATER_LEVELS)]),
                                   '; '.join(str(c) for c in game['water2'])[:300])


def main():
    ap = argparse.ArgumentParser()
    for n in ('dump', 'ult', 'body', 'vl', 'model', 'mario', 'out'):
        ap.add_argument(n)
    ap.add_argument('--param', help="the fighter_param.bin to give his stats (written to OUT/param/fighter)")
    ap.add_argument('--bank', help="tools/vfxb_to_ptcl.py's output folder (pzenigame.010d0000.ptcl / .efc)")
    ap.add_argument('--sound', help="tools/ultimate_sound.py's output folder")
    a = ap.parse_args()
    fighter = os.path.join(a.out, 'fighter/pzenigame')
    param = os.path.join(a.out, 'param/fighter')
    print(body_scripts(a, fighter, param))
    print(special_slots(fighter, a.body))
    msc = os.path.join(fighter, 'script/msc')
    compile_msc(os.path.join(PZDIR, 'pzenigame.c'), os.path.join(msc, 'pzenigame.mscsb'))
    compile_msc(os.path.join(PZDIR, 'weapons/water.c'), os.path.join(msc, 'water/water.mscsb'))
    print(water_scripts(a, fighter))
    if a.param:
        run(os.path.join(HERE, 'fighter_param.py'), 'set', a.param, os.path.join(param, 'fighter_param.bin'),
            str(KIND), *STATS)
    if a.sound:
        assert not json.load(open(os.path.join(a.sound, 'sound_ids.json')))['_rows'], 'ids would move: not done here'
        shutil.copytree(os.path.join(a.sound, 'fighter/pzenigame/sound'), os.path.join(fighter, 'sound'), dirs_exist_ok=True)
        shutil.copytree(os.path.join(a.sound, 'sound'), os.path.join(a.out, 'sound'), dirs_exist_ok=True)
    if a.bank:
        d = os.path.join(fighter, 'effect/pzenigame')
        os.makedirs(d, exist_ok=True)
        for ext in ('ptcl', 'efc'):
            shutil.copy(os.path.join(a.bank, 'pzenigame.010d0000.' + ext), d)


if __name__ == '__main__':
    main()
