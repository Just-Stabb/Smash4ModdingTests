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
- his articles (tools/extra_kinds.json "weapons": fireball, spark, tornado, flash, explosion, deathball, crash,
  sleep): script/msc/<name>/<name>.mscsb from fighters/brave/weapons/ (thunder_base.c + fireball.c, or +
  placed.c + spark.c / tornado.c / crash.c, or + shot.c + flash.c / explosion.c / deathball.c / sleep.c) and
  script/animcmd/weapon/<name>/ (Ultimate's brave_<name> scripts: ARTICLES);
- --rpx: code/cross_f.rpx = IN.rpx + kind_expand / weapon_expand / base_effects_cave / base_customs_cave /
  trait_badge_cave (the damage panel: Kirby's trait badge and Hero's Command Selection menu and MP gauge) /
  brave_reflect_cave (a reflector group for Robin's kind: Bounce) /
  thunder_orb_cave (Robin's native Thunder orb only on his own Thunder, not on Hero's copies) /
  trail_table_cave / kirby_stat_cave's profile table (Acceleratle's speeds) (re-applying them over an executable that has them gives it back, so IN can be the
  last test's);
- --menu DIR --menu-layout ARC [--menu-font FONT]: ui/info/dmg/ = DIR (the damage panel with the trait
  badge) + Hero's Command Selection window and MP gauge from Ultimate's (ARC: its info_melee layout.arc;
  tools/brave_menu_art.py, tools/dmg_brave_menu.py);
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
CONDS = ['SUCCESS_SP']          # the scripts' MP checks: his MSC decides (brave_cost), a script runs as cast
# the articles' motion slots (thunder's motion info has 24 entries, the rest name empty scripts): the fireball
# (fireball.c: func_24(level) flies, func_24(3 + level) bursts), spark / tornado (placed.c: func_24(level),
# 23 while the spark waits)
def _slots(name, used):
    return tuple(used) + tuple('%snone%d' % (name, i) for i in range(len(used), 24))


ARTICLES = {
    'fireball': (_slots('fireball', ('specialn1', 'specialn2', 'specialn3', 'bursts', 'burstm', 'burstl')),
                 {'fireball1': 0, 'fireball2': 0}),             # Frizzle's two balls
    'spark': (_slots('spark', ('specials1', 'specials2', 'specials32')), {}),
    'tornado': (_slots('tornado', ('specialhi1', 'specialhi2', 'specialhi3')), {'tornado1': 0, 'tornado2': 0}),
    # Command Selection's (shot.c: motion level flies, 2 + level the hit's; crash: placed.c)
    'flash': (_slots('flash', ('flash1', 'flash2', 'flashhit1', 'flashhit2')), {}),
    'explosion': (_slots('explosion', ('move1', 'move2', 'explode1', 'explode2')), {}),
    'deathball': (_slots('deathball', ('deathball1', 'deathball2', 'deathballko')), {'deathball': 0}),
    'crash': (_slots('crash', ('crash1', 'crash2', 'crashend1', 'crash1mp20', 'crash1mp40', 'crash1mp60',
                               'crash1mp80')), {}),
    'sleep': (_slots('sleep', ('sleep',)), {}),
}
# each article's MSC: weapons/thunder_base.c, this, then weapons/<name>.c
KASWOOSH_SPREAD = 7.0      # half the two whirlwinds' distance (their ellipses' centres, 7.4 out)
KASWOOSH_LAUNCH = 50       # Kaswoosh's launching hit: 2 frames before its 52 (weapons/tornado.c)
ARTICLE_BASE = {'fireball': None, 'spark': 'placed', 'tornado': 'placed', 'crash': 'placed', 'flash': 'shot',
                'explosion': 'shot', 'deathball': 'shot', 'sleep': 'shot'}
# Magic Burst with less MP (weapons/crash.c): Crash1 with each hit's damage x MP / 100
CRASH_TIERS = {'crash1mp%d' % m: m / 100.0 for m in (20, 40, 60, 80)}
# Whack's KO (weapons/deathball.c): DeathBall1's hitbox as ID 2, hit group 2, effect 0x10 (Death: Smash Run's
# Orne, a KO on the spot), 1 damage, radius 10 around Y 8, no clank / rebound, fighters only, unblockable,
# not reflectable / absorbable, for 2 frames
DEATH = 0x10
KO_HITBOX = {0: 2, 1: 2, 3: 1.0, 4: 361, 5: 0, 6: 0, 7: 0, 8: 10.0, 9: 0.0, 10: 8.0, 11: 0.0, 12: DEATH, 16: 0,
             17: 0, 24: 1, 28: 0, 29: 0, 30: 0}
# motions whose effects play out after the article is removed (its explosions)
LASTING = ('burst', 'flashhit', 'explode', 'crash')
CAVES = ('kind_expand', 'weapon_expand', 'base_effects_cave', 'base_customs_cave', 'trait_badge_cave',
         'brave_reflect_cave', 'thunder_orb_cave')


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def compile_msc(srcs, out_path):
    """srcs compiled as one file (an article's: weapons/thunder_base.c then its own)"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with tempfile.NamedTemporaryFile('w', suffix='.c', delete=False) as f:
        for src in srcs:
            f.write(open(src).read() + '\n')
    try:
        run(os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'), f.name, '-o', out_path)
    finally:
        os.unlink(f.name)
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


def article_scripts(a, name, wdir):
    """an article's game / effect scripts from Ultimate's brave_<name> ones (hitboxes and effects on its bone
    0: it has no model); sound empty (his sounds aren't converted yet)"""
    motions, joints = ARTICLES[name]
    ids = {}
    for path in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(BRAVE, 'brave_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
    game, effect = {}, {}
    U.EFFECT_CONDS = (U.LR_LEFT,)
    gtr, etr = U.Translator(joints), U.EffectTranslator(joints, ids, {})
    src_dir = os.path.join(a.dump, 'brave_' + name)
    for fname in sorted(os.listdir(src_dir)):
        mo = fname[:-4].lower()
        fns = U.functions(open(os.path.join(src_dir, fname)).read())
        assert mo in motions, mo
        game[mo] = gtr.script(fns['game_' + mo]) if 'game_' + mo in fns else [acmd.Command(acmd.END)]
        etr.last = False
        effect[mo] = etr.script(fns['effect_' + mo]) if 'effect_' + mo in fns else [acmd.Command(acmd.END)]
        if mo.startswith(LASTING):
            # the explosion plays out after the article is removed (fireball.c / shot.c remove it after
            # the burst's frames; Ultimate's scripts at a notify)
            for c in effect[mo]:
                if c.name.startswith('Graphic_Effect'):
                    c.params[-1] = 0
    U.EFFECT_CONDS = ()
    assert not etr.missing, etr.missing
    if name == 'crash':
        for mo, k in CRASH_TIERS.items():
            game[mo] = [acmd.Command(c.ident, list(c.params)) for c in game['crash1']]
            for c in game[mo]:
                if c.name in ('Hitbox', 'Special_Hitbox', 'Extended_Hitbox', 'Extended_Special_Hitbox'):
                    c.params[3] = round(c.params[3] * k, 2)
            effect[mo] = effect['crash1']
    if name == 'tornado':
        # Kaswoosh's two whirlwinds: Ultimate's on the article's bones Tornado1 / Tornado2, which its
        # d02specialhi3 animation sends round an ellipse each, 7.4 out along Z (the article's screen axis:
        # Robin's Arcthunder spreads its hitboxes along Z) either side, +-9.7 along Z and +-3.8 along X,
        # every 16 frames. The effects move so in the bank (vfxb_to_ptcl.py --bone-path: the README's
        # build), on bone 0 here as Ultimate's on theirs (the second turned 180 about Y: the other
        # ellipse); the hitboxes (IDs 0 / 2 / 4 on Tornado1, 1 / 3 / 5 on Tornado2; 6, on top, stays)
        # KASWOOSH_SPREAD apart along Z, the ellipses' centres
        for c in game['specialhi3']:
            if c.name in ('Special_Hitbox', 'Extended_Special_Hitbox') and c.params[0] < 6:
                dz = KASWOOSH_SPREAD * (1 if c.params[0] % 2 == 0 else -1)   # Tornado1's on +Z
                c.params[11] += dz
                if c.name == 'Extended_Special_Hitbox':
                    c.params[-1] += dz
        # its launch: Ultimate's second set of hitboxes (part 1) is under `if life <= 2`, which the
        # translator drops; tornado.c gives Kaswoosh 52 frames (placed_life), so at frame 50. Swoosh's
        # converted launcher as the template, Ultimate's values (4%, 120, KBG 125, BKB 85, size 8.5)
        tpl = next(c for c in game['specialhi2'] if c.name == 'Extended_Special_Hitbox' and c.params[1] == 1)
        launch = [acmd.Command(acmd.BY_NAME['frame'], [KASWOOSH_LAUNCH])]
        for i, y, z, y2 in ((0, 4.5, 1, 4.5), (1, 4.5, -1, 4.5), (2, 12.5, 1, 12.5), (3, 12.5, -1, 12.5),
                            (4, 21.0, 1, 21.0), (5, 21.0, -1, 21.0), (6, 5.0, 0, 20.0)):
            hb = acmd.Command(tpl.ident, list(tpl.params))
            hb.params[0], hb.params[1] = i, 1
            hb.params[3:9] = [4.0, 120, 125, 0, 85, 8.5]
            hb.params[9:12] = [0.0, y, z * KASWOOSH_SPREAD]
            hb.params[14] = 0.6
            hb.params[-3:] = [0.0, y2, z * KASWOOSH_SPREAD]
            launch.append(hb)
        end = [c for c in game['specialhi3'] if c.ident == acmd.END]
        game['specialhi3'] = [c for c in game['specialhi3'] if c.ident != acmd.END] + launch + end
        whirls = [c for c in effect['specialhi3'] if c.name == 'External_Graphic']
        assert len(whirls) == 2, whirls
    if name == 'deathball':
        hb = next(c for c in game['deathball1'] if c.name == 'Extended_Special_Hitbox')
        ko = acmd.Command(hb.ident, list(hb.params))
        for i, v in KO_HITBOX.items():
            ko.params[i] = v
        ko.params[-3:] = [0.0, 8.0, 0.5]            # the capsule's other end (never its start: that hits the whole stage)
        game['deathballko'] = [ko, acmd.Command(acmd.BY_NAME['wait'], [2]),
                               acmd.Command(acmd.BY_NAME['remove_all_hitboxes'], []), acmd.Command(acmd.END)]
    os.makedirs(wdir, exist_ok=True)
    end = [acmd.Command(acmd.END)]
    for fn, sc in (('game', game), ('effect', effect), ('sound', {})):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, end) for n in motions}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in motions))
    return '%s: %s; left out %s %s' % (name, ', '.join(sorted(game)), gtr.skipped, etr.skipped)


def main():
    ap = argparse.ArgumentParser()
    for n in ('dump', 'hero', 'body', 'vl', 'model', 'out'):
        ap.add_argument(n)
    ap.add_argument('--rpx')
    ap.add_argument('--bank')
    ap.add_argument('--trails')
    ap.add_argument('--motions')
    ap.add_argument('--menu')
    ap.add_argument('--menu-font', help='the font for the menu (the Wii U shared font: Cemu\'s '
                    'resources/sharedFonts/CafeStd.ttf)')
    ap.add_argument('--menu-layout', help="with --menu: Ultimate's ui/layout/info/info_melee/info_melee/layout.arc "
                    '(the window, pointer and gauge are its)')
    a = ap.parse_args()
    fighter = os.path.join(a.out, 'fighter/brave')
    print(body_scripts(a, fighter, os.path.join(a.out, 'param/fighter')))

    msc = os.path.join(fighter, 'script/msc')
    compile_msc([os.path.join(BRAVE, 'brave.c')], os.path.join(msc, 'brave.mscsb'))
    w = os.path.join(BRAVE, 'weapons')
    for name in ARTICLES:
        base = ARTICLE_BASE[name]
        srcs = [os.path.join(w, 'thunder_base.c')] + ([os.path.join(w, base + '.c')] if base else [])
        compile_msc(srcs + [os.path.join(w, name + '.c')], os.path.join(msc, name, name + '.mscsb'))
        print(article_scripts(a, name, os.path.join(fighter, 'script/animcmd/weapon', name)))

    if a.rpx:
        os.makedirs(os.path.join(a.out, 'code'), exist_ok=True)
        argv = []
        for g in CAVES:
            argv += run(os.path.join(HERE, g + '.py')).split()
        argv += run(os.path.join(HERE, 'trail_table_cave.py'), a.rpx).split()
        argv += run(os.path.join(HERE, 'kirby_stat_cave.py'), '--table').split()    # Acceleratle's profile 3
        run(os.path.join(HERE, 'rpx_patch.py'), a.rpx, os.path.join(a.out, 'code/cross_f.rpx'), *argv)
    if a.bank:
        d = os.path.join(fighter, 'effect/brave')
        os.makedirs(d, exist_ok=True)
        for ext in ('ptcl', 'efc'):
            shutil.copy(os.path.join(a.bank, 'reflet.010d0000.' + ext), os.path.join(d, 'brave.010d0000.' + ext))
    if a.trails:
        shutil.copytree(a.trails, os.path.join(fighter, 'effect/brave/trail'), dirs_exist_ok=True)
    if a.menu:
        import dmg_brave_menu
        with tempfile.TemporaryDirectory() as art:
            run(os.path.join(HERE, 'brave_menu_art.py'), a.menu_layout, art,
                *(['--font', a.menu_font] if a.menu_font else []))
            print('menu: sprites from 0x%X, texture slot %d' % dmg_brave_menu.build(
                a.menu, art, os.path.join(a.out, 'ui/info/dmg')))
    if a.motions:
        d = os.path.join(fighter, 'motion/body')
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(a.motions, 'motion/body/main.pac'), os.path.join(d, 'main.pac'))


if __name__ == '__main__':
    main()
