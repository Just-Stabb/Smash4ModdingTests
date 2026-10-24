#!/usr/bin/env python3
"""Hero's moves (fighters/brave/README.md): his scripts, MSC, the fireball article and the executable.

  python3 tools/brave_build.py DUMP HERO BRAVE_BODY VL MODEL OUT [--rpx IN.rpx] [--bank DIR] [--motions DIR]
                               [--trails DIR]

DUMP: the smashline dump's lua2cpp_brave (brave/, brave_fireball/, ...); HERO: Ultimate's fighter/brave
(motion/body/c00/motion_list.bin, model/body/c00/model.nusktb); BRAVE_BODY: his folder's
script/animcmd/body (Robin's, universal-mechanics game.bin); VL: Robin's fighter_param_vl_reflet.bin;
MODEL: his converted model/body/c00 (the ACMD joint ids). Writes OUT/:
- fighter/brave/script/animcmd/body/: tools/ultimate_acmd.py with fighters/brave/specials_acmd.json (his
  normals plus the specials in Robin's special slots; Ultimate's MP checks taken as passed, SUCCESS_SP),
  his effects (fighters/brave/brave_effects.json), the bone-turned ones moved to their variants
  (tools/effect_variants.py apply); param/fighter/fighter_param_vl_brave.bin;
- fighter/brave/script/msc/brave.mscsb from fighters/brave/brave.c;
- the fireball article (tools/extra_kinds.json "weapons"): script/msc/fireball/fireball.mscsb from
  fighters/brave/weapons/fireball.c and script/animcmd/weapon/fireball/ (Ultimate's brave_fireball
  scripts: FIREBALL_MOTIONS);
- --rpx: code/cross_f.rpx = IN.rpx + kind_expand / weapon_expand / base_effects_cave / base_customs_cave /
  trail_table_cave (re-applying them over an executable that has them gives it back, so IN can be the
  last test's);
- --bank: effect/brave/brave.010d0000.{ptcl,efc} from DIR/reflet.010d0000.* (tools/vfxb_to_ptcl.py);
- --trails: effect/brave/trail/ from DIR (tools/ultimate_trails.py --shader 3);
- --motions: motion/body/main.pac from DIR/motion/body (tools/ultimate_fighter.py motions --add).
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
import ultimate_acmd as U  # noqa: E402

BRAVE = os.path.join(ROOT, 'fighters', 'brave')
CONDS = ['SUCCESS_SP']          # the MP checks: no MP yet, every cast works
# the fireball's motion slots (fireball.c: func_24(level) flies, func_24(3 + level) bursts); thunder's
# motion info has 24 entries, the rest name empty scripts
FIREBALL_MOTIONS = ('specialn1', 'specialn2', 'specialn3', 'bursts', 'burstm', 'burstl') + tuple(
    'fireballnone%d' % i for i in range(6, 24))
CAVES = ('kind_expand', 'weapon_expand', 'base_effects_cave', 'base_customs_cave')


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def compile_msc(src, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    run(os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'), src, '-o', out_path)
    assert os.path.getsize(out_path) > 0


def body_scripts(a, fighter, param):
    out = os.path.join(fighter, 'script/animcmd/body')
    os.makedirs(out, exist_ok=True)
    os.makedirs(param, exist_ok=True)
    ids = os.path.join(BRAVE, 'brave_effects.json')
    with tempfile.TemporaryDirectory() as tmp:
        log = run(os.path.join(HERE, 'ultimate_acmd.py'), os.path.join(a.dump, 'brave'),
                  os.path.join(a.body, 'game.bin'), os.path.join(out, 'game.bin'), a.model,
                  '--have', 'Shield,Sword1', '--others', a.body, tmp,
                  '--motion-list', os.path.join(a.hero, 'motion/body/c00/motion_list.bin'),
                  '--mtable', os.path.join(a.body, 'motion.mtable'), os.path.join(out, 'motion.mtable'),
                  '--vl', a.vl, os.path.join(param, 'fighter_param_vl_brave.bin'), '--vl-kind', 'reflet',
                  '--effects', os.path.join(ROOT, 'reference/ultimate_sys_effects.json') + ',' + ids,
                  os.path.join(a.hero, 'model/body/c00/model.nusktb'),
                  '--translate', os.path.join(BRAVE, 'specials_acmd.json'), *sum((['--cond', c] for c in CONDS), []))
        log += run(os.path.join(HERE, 'effect_variants.py'), 'apply', os.path.join(tmp, 'effect.bin'), ids,
                   os.path.join(out, 'effect.bin'))
        for fn in ('sound.bin', 'expression.bin'):
            shutil.copy(os.path.join(tmp, fn), os.path.join(out, fn))
    return log


def fireball_scripts(a, wdir):
    """the fireball's game / effect scripts from Ultimate's brave_fireball ones (hitboxes and effects on its
    bone 0: it has no model, Frizzle's two balls are one); sound empty (his sounds aren't converted yet)"""
    ids = {}
    for path in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(BRAVE, 'brave_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
    game, effect = {}, {}
    U.EFFECT_CONDS = (U.LR_LEFT,)
    joints = {'fireball1': 0, 'fireball2': 0}       # Frizzle's two balls (bones of Ultimate's article model)
    gtr, etr = U.Translator(joints), U.EffectTranslator(joints, ids, {})
    src_dir = os.path.join(a.dump, 'brave_fireball')
    for fname in sorted(os.listdir(src_dir)):
        name = fname[:-4].lower()
        fns = U.functions(open(os.path.join(src_dir, fname)).read())
        assert name in FIREBALL_MOTIONS, name
        game[name] = gtr.script(fns['game_' + name]) if 'game_' + name in fns else [acmd.Command(acmd.END)]
        etr.last = False
        effect[name] = etr.script(fns['effect_' + name])
        if name.startswith('burst'):
            # the explosion plays out after the article is removed (fireball.c removes it after the
            # burst's frames; Ultimate's scripts at a notify)
            for c in effect[name]:
                if c.name.startswith('Graphic_Effect'):
                    c.params[-1] = 0
    U.EFFECT_CONDS = ()
    assert not etr.missing, etr.missing
    os.makedirs(wdir, exist_ok=True)
    end = [acmd.Command(acmd.END)]
    for fn, sc in (('game', game), ('effect', effect), ('sound', {})):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, end) for n in FIREBALL_MOTIONS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FIREBALL_MOTIONS))
    return 'fireball: %s; left out %s %s' % (', '.join(sorted(game)), gtr.skipped, etr.skipped)


def main():
    ap = argparse.ArgumentParser()
    for n in ('dump', 'hero', 'body', 'vl', 'model', 'out'):
        ap.add_argument(n)
    ap.add_argument('--rpx')
    ap.add_argument('--bank')
    ap.add_argument('--trails')
    ap.add_argument('--motions')
    a = ap.parse_args()
    fighter = os.path.join(a.out, 'fighter/brave')
    print(body_scripts(a, fighter, os.path.join(a.out, 'param/fighter')))

    msc = os.path.join(fighter, 'script/msc')
    compile_msc(os.path.join(BRAVE, 'brave.c'), os.path.join(msc, 'brave.mscsb'))
    compile_msc(os.path.join(BRAVE, 'weapons/fireball.c'), os.path.join(msc, 'fireball/fireball.mscsb'))
    print(fireball_scripts(a, os.path.join(fighter, 'script/animcmd/weapon/fireball')))

    if a.rpx:
        os.makedirs(os.path.join(a.out, 'code'), exist_ok=True)
        argv = []
        for g in CAVES:
            argv += run(os.path.join(HERE, g + '.py')).split()
        argv += run(os.path.join(HERE, 'trail_table_cave.py'), a.rpx).split()
        run(os.path.join(HERE, 'rpx_patch.py'), a.rpx, os.path.join(a.out, 'code/cross_f.rpx'), *argv)
    if a.bank:
        d = os.path.join(fighter, 'effect/brave')
        os.makedirs(d, exist_ok=True)
        for ext in ('ptcl', 'efc'):
            shutil.copy(os.path.join(a.bank, 'reflet.010d0000.' + ext), os.path.join(d, 'brave.010d0000.' + ext))
    if a.trails:
        shutil.copytree(a.trails, os.path.join(fighter, 'effect/brave/trail'), dirs_exist_ok=True)
    if a.motions:
        d = os.path.join(fighter, 'motion/body')
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(a.motions, 'motion/body/main.pac'), os.path.join(d, 'main.pac'))


if __name__ == '__main__':
    main()
