#!/usr/bin/env python3
"""Sephiroth's specials (fighters/edge/specials.md): his scripts, MSC, new articles and executable.

  python3 tools/edge_specials_build.py DUMP EDGE ZELDA ZELDA_UM VL MODEL OUT [--rpx IN.rpx]
                                       [--bank DIR] [--motions DIR]

DUMP: the smashline dump's lua2cpp_edge (edge/, edge_fire/, ...); EDGE: Ultimate's fighter/edge
(motion/body/c00/motion_list.bin, model/body/c00/model.nusktb); ZELDA: vanilla fighter/zelda;
ZELDA_UM: Zelda's universal-mechanics script/animcmd/body (its game.bin); VL: vanilla
fighter_param_vl_zelda.bin; MODEL: his converted model/body/c00 (the ACMD joint ids). Writes OUT/:
- fighter/edge/script/animcmd/body/: tools/ultimate_acmd.py with fighters/edge/specials_acmd.json
  (his normals as before plus the specials in Zelda's special slots), the effects moved to their
  turned variants (tools/effect_variants.py apply); param/fighter/fighter_param_vl_edge.bin;
- fighter/edge/script/msc/edge.mscsb from fighters/edge/edge.c;
- the new articles (tools/extra_kinds.json "weapons", after Zelda's five): fire (Flare / Megaflare /
  Gigaflare): script/msc/fire/fire.mscsb from fighters/edge/weapons/fire.c and
  script/animcmd/weapon/fire/ (Ultimate's edge_fire scripts: FIRE_MOTIONS); flare1 / flare2 / flash
  (moves not made yet): Zelda's dein files under their names, so every article has its files;
- --rpx: code/cross_f.rpx = IN.rpx + tools/kind_expand.py + tools/weapon_expand.py (re-applying
  them over an executable that has them gives it back, so IN can be the last test's);
- --bank: effect/edge/edge.010d0000.{ptcl,efc} from DIR/zelda.010d0000.* (tools/vfxb_to_ptcl.py);
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

EDGE = os.path.join(ROOT, 'fighters', 'edge')
# the fire article's motion slots (dein's 8; fire.c: func_24(level) flies, func_24(4 + level) bursts)
FIRE_MOTIONS = ('specialn1', 'specialn2', 'specialn3', 'firenone3', 'bursts', 'burstm', 'burstl', 'firenone7')
PLACEHOLDERS = ('flare1', 'flare2', 'flash')


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
    """his body scripts and vl file (the run that made test 53's effect.bin and test 22's game.bin,
    plus specials_acmd.json)"""
    out = os.path.join(fighter, 'script/animcmd/body')
    os.makedirs(out, exist_ok=True)
    os.makedirs(param, exist_ok=True)
    ids = os.path.join(EDGE, 'edge_effects.json')
    with tempfile.TemporaryDirectory() as tmp:
        log = run(os.path.join(HERE, 'ultimate_acmd.py'), os.path.join(a.dump, 'edge'),
                  os.path.join(a.zelda_um, 'game.bin'), os.path.join(out, 'game.bin'), a.model,
                  '--have', 'SwordL1,SwordR1', '--others', os.path.join(a.zelda, 'script/animcmd/body'), tmp,
                  '--motion-list', os.path.join(a.edge, 'motion/body/c00/motion_list.bin'),
                  '--mtable', os.path.join(a.zelda, 'script/animcmd/body/motion.mtable'),
                  os.path.join(out, 'motion.mtable'),
                  '--vl', a.vl, os.path.join(param, 'fighter_param_vl_edge.bin'),
                  '--effects', os.path.join(ROOT, 'reference/ultimate_sys_effects.json') + ',' + ids,
                  os.path.join(a.edge, 'model/body/c00/model.nusktb'),
                  '--translate', os.path.join(EDGE, 'specials_acmd.json'))
        log += run(os.path.join(HERE, 'effect_variants.py'), 'apply', os.path.join(tmp, 'effect.bin'), ids,
                   os.path.join(out, 'effect.bin'))
        for fn in ('sound.bin', 'expression.bin'):
            shutil.copy(os.path.join(tmp, fn), os.path.join(out, fn))
    return log


def fire_scripts(a, wdir):
    """the fire article's game / effect scripts from Ultimate's edge_fire ones (hitboxes and effects
    on its bone 0); sound empty (his sounds aren't converted yet)"""
    ids = {}
    for path in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(EDGE, 'edge_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
    game, effect = {}, {}
    U.EFFECT_CONDS = (U.LR_LEFT,)
    gtr, etr = U.Translator({}), U.EffectTranslator({}, ids, {})
    src_dir = os.path.join(a.dump, 'edge_fire')
    for fname in sorted(os.listdir(src_dir)):
        name = fname[:-4].lower()
        fns = U.functions(open(os.path.join(src_dir, fname)).read())
        assert name in FIRE_MOTIONS, name
        game[name] = gtr.script(fns['game_' + name])
        etr.last = False
        effect[name] = etr.script(fns['effect_' + name])
        if name.startswith('burst'):
            # the explosion plays out after the article is removed (fire.c removes it at the end of
            # its hitboxes; Ultimate's scripts at a notify, 6 / 20 / 45)
            for c in effect[name]:
                if c.name == 'Graphic_Effect2':
                    c.params[-1] = 0
    U.EFFECT_CONDS = ()
    assert not etr.missing, etr.missing
    os.makedirs(wdir, exist_ok=True)
    end = [acmd.Command(acmd.END)]
    for fn, sc in (('game', game), ('effect', effect), ('sound', {})):          # dein's files
        acmd.ACMDFile({acmd.crc(n): sc.get(n, end) for n in FIRE_MOTIONS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FIRE_MOTIONS))
    return 'fire: %s; left out %s %s' % (', '.join(sorted(game)), gtr.skipped, etr.skipped)


def main():
    ap = argparse.ArgumentParser()
    for n in ('dump', 'edge', 'zelda', 'zelda_um', 'vl', 'model', 'out'):
        ap.add_argument(n)
    ap.add_argument('--rpx')
    ap.add_argument('--bank')
    ap.add_argument('--motions')
    a = ap.parse_args()
    fighter = os.path.join(a.out, 'fighter/edge')
    print(body_scripts(a, fighter, os.path.join(a.out, 'param/fighter')))

    msc = os.path.join(fighter, 'script/msc')
    compile_msc(os.path.join(EDGE, 'edge.c'), os.path.join(msc, 'edge.mscsb'))
    compile_msc(os.path.join(EDGE, 'weapons/fire.c'), os.path.join(msc, 'fire/fire.mscsb'))
    print(fire_scripts(a, os.path.join(fighter, 'script/animcmd/weapon/fire')))
    for name in PLACEHOLDERS:
        os.makedirs(os.path.join(msc, name), exist_ok=True)
        shutil.copy(os.path.join(a.zelda, 'script/msc/dein/dein.mscsb'), os.path.join(msc, name, name + '.mscsb'))
        shutil.copytree(os.path.join(a.zelda, 'script/animcmd/weapon/dein'),
                        os.path.join(fighter, 'script/animcmd/weapon', name), dirs_exist_ok=True)

    if a.rpx:
        import kind_expand
        import weapon_expand
        os.makedirs(os.path.join(a.out, 'code'), exist_ok=True)
        run(os.path.join(HERE, 'rpx_patch.py'), a.rpx, os.path.join(a.out, 'code/cross_f.rpx'),
            *kind_expand.args(kind_expand.build()[0]), *weapon_expand.args(weapon_expand.build()[0]))
    if a.bank:
        d = os.path.join(fighter, 'effect/edge')
        os.makedirs(d, exist_ok=True)
        for ext in ('ptcl', 'efc'):
            shutil.copy(os.path.join(a.bank, 'zelda.010d0000.' + ext), os.path.join(d, 'edge.010d0000.' + ext))
    if a.motions:
        d = os.path.join(fighter, 'motion/body')
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(a.motions, 'motion/body/main.pac'), os.path.join(d, 'main.pac'))


if __name__ == '__main__':
    main()
