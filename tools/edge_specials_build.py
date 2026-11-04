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
  script/animcmd/weapon/fire/ (Ultimate's edge_fire scripts: FIRE_MOTIONS); flash (Scintilla):
  fighters/edge/weapons/flash.c and Ultimate's edge_flash Attack in tiers (FLASH_MOTIONS); flare1 (Shadow
  Flare: the shot and, after a hit, the orbs): fighters/edge/weapons/flare1.c and Ultimate's edge_flare1 / edge_flare2
  scripts (FLARE1_MOTIONS); flare2 (unused: flare1 plays the orbs): Zelda's dein files under its name;
- --rpx: code/cross_f.rpx = IN.rpx + tools/kind_expand.py + tools/weapon_expand.py +
  tools/edge_counter_cave.py (Scintilla's counter shape) + tools/effect_heap_patch.py (the effect heap 44 -> 60
  MiB: his bank ran it out, test 61 / 62) + tools/acmd_ext_cave.py last (its var_entry hook; Shadow Flare's shared
  slot variables); re-applying them over an executable that has them gives it back, so IN
  can be the last test's;
- --bank: effect/edge/edge.010d0000.{ptcl,efc} from DIR/zelda.010d0000.* (tools/vfxb_to_ptcl.py);
- --motions: motion/body/main.pac from DIR/motion/body (tools/ultimate_fighter.py motions --add).
"""
import argparse
import json
import os
import re
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
PLACEHOLDERS = ('flare2',)
# flare1 (Shadow Flare, weapons/flare1.c): the shot, its hit / end, the orbs' hitboxes (the object is the flaredummy
# and its flare2 orbs too after a hit)
FLARE1_MOTIONS = ('fly', 'hit', 'end', 'orbit', 'flarenone4', 'flarenone5', 'flarenone6', 'flarenone7')
# the flash article's motion slots (flash.c: motion = the tier Sephiroth's edge_lw_generate passes): 0 the whiff,
# 1-5 a counter at ATTACK_RATIO p = 0, .25, .5, .75, 1 (Smash 4's ACMD has no hitbox lerp: one script a tier)
FLASH_MOTIONS = ('attacknohit', 'attack0', 'attack1', 'attack2', 'attack3', 'attack4', 'flashnone6', 'flashnone7')
FLASH_RATIOS = (None, 0.0, 0.25, 0.5, 0.75, 1.0)
# his down special's game scripts left empty: game_speciallwhit's countered / whiff branches (speed, XLU, the
# flash, the whiff's motion rates) are edge.c's (edge_lw_hit_*), by the motion frame
EMPTY_GAME = ('speciallwhit', 'specialairlwhit')


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def effect_ids():
    ids = {}
    for path in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(EDGE, 'edge_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
    return ids


FX_RE = re.compile(r'(return )(0x[0-9A-Fa-f]+|0)(; \} // fx (\S+))')


def compile_msc(src, out_path):
    """msclang; the effect ids MSC uses (`int f() { return ID; } // fx NAME`) written in from edge_effects.json
    (0 when not in his bank yet)"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = open(src).read()
    ids = effect_ids()
    missing = []

    def fx(m):
        if m.group(4) not in ids:
            missing.append(m.group(4))
        return '%s0x%X%s' % (m.group(1), ids.get(m.group(4), 0), m.group(3))
    text = FX_RE.sub(fx, text)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, os.path.basename(src))
        with open(path, 'w') as f:
            f.write(text)
        run(os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'), path, '-o', out_path)
    assert os.path.getsize(out_path) > 0
    return '%s: effects not in his bank (left out): %s' % (os.path.basename(src), ', '.join(missing) or '-')


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
    game = acmd.ACMDFile.load(os.path.join(out, 'game.bin'))
    for name in EMPTY_GAME:
        game.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
    game.save(os.path.join(out, 'game.bin'))
    return log


def fire_scripts(a, wdir):
    """the fire article's game / effect scripts from Ultimate's edge_fire ones (hitboxes and effects
    on its bone 0); sound empty (his sounds aren't converted yet)"""
    ids = effect_ids()
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


def _args(text):
    """a macro call's arguments (top-level commas)"""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _calls(body, macro):
    """[(start, end, [args])] of `macros::MACRO(...)` in body"""
    out = []
    for m in re.finditer(r'macros::%s\(' % macro, body):
        i, depth = m.end(), 1
        while depth:
            depth += {'(': 1, ')': -1}.get(body[i], 0)
            i += 1
        out.append((m.start(), i, _args(body[m.end():i - 1])))
    return out


# ATTACK's arguments (after agent) that the lerp interpolates: damage, KBG, FKB, BKB, size, hitlag, SDI,
# shield damage (Ultimate's ATK lerp: every numeric field, inferred; the angle, effect and flags are the same in
# both ids); the sound level: id 1's from p 0.5 (L on the last hit)
LERP = {4: 'f', 6: 'i', 7: 'i', 8: 'i', 9: 'f', 16: 'f', 17: 'f', 21: 'i'}


def flash_attack(a0, a1, p):
    out = list(a0)
    for k, kind in LERP.items():
        v = float(a0[k]) + (float(a1[k]) - float(a0[k])) * p
        out[k] = str(int(round(v))) if kind == 'i' else '%.3f' % v
    if p >= 0.5:
        out[34] = a1[34]
    out[1] = '0'
    return 'macros::ATTACK(%s);' % ', '.join(out)


def flash_scripts(a, wdir):
    """the flash article's game / effect scripts: Ultimate's edge_flash Attack per tier (FLASH_MOTIONS). Game: the
    whiff's hitboxes (FLAG_HIT off) or the counter's id 0 -> id 1 at the tier's p (ATTACK_SET_LERP +
    ATK_LERP_RATIO); its frame-16 notify (removal) is flash.c's. Effect: the effects scaled as its exec (31950)
    scales the last one made each frame (EFFECT_ID): every one but the first puff (replaced by edge_senkou_hold
    in the same frame) at effect_scale_no_hit 0.65 / 1.2 + 0.8 p. Sound empty (none of his converted)"""
    src = open(os.path.join(a.dump, 'edge_flash', 'Attack.txt')).read()
    fns = U.functions(src)
    atk = [c[2] for c in _calls(fns['game_attack'], 'ATTACK')]
    assert len(atk) == 6, len(atk)     # whiff f0, f15; counter f0 id 0, 1; f15 id 0, 1
    ids = effect_ids()
    gtr, etr = U.Translator({}), U.EffectTranslator({}, ids, {})
    game, effect, missing = {}, {}, set()
    U.EFFECT_CONDS = (U.LR_LEFT,)
    ebody = fns['effect_attack']
    efx = _calls(ebody, 'EFFECT_FOLLOW_RND') + _calls(ebody, 'EFFECT_FOLLOW')
    first = min(s for s, _e, _a in efx)
    for name, p in zip(FLASH_MOTIONS, FLASH_RATIOS):
        if p is None:
            f0, f15 = ('macros::ATTACK(%s);' % ', '.join(x) for x in atk[:2])
            scale = 0.65
        else:
            f0, f15 = flash_attack(atk[2], atk[3], p), flash_attack(atk[4], atk[5], p)
            scale = 1.2 + 0.8 * p
        # the finisher in Part 1, its own hit log: Smash 4 keeps Part 0's records (the multi-hit's) over
        # Remove_All_Hitboxes, so the finisher missed whoever the multi-hit had hit (test 65; Ultimate's clear_all
        # clears them). As Supamario's Kamehameha finish
        f15 = re.sub(r'^(macros::ATTACK\(agent, \d+, )0,', r'\g<1>1,', f15)
        body = ('if macros::is_excute(agent) {\n%s\n}\nframe(agent.lua_state_agent, 15.0);\n'
                'if macros::is_excute(agent) {\nAttackModule::clear_all(agent.module_accessor);\n%s\n}\n' % (f0, f15))
        game[name] = gtr.script(body)
        text, at = '', 0
        for s, e, args in sorted(efx):
            if s != first:
                args = list(args)
                args[9] = '%.3f' % (float(args[9]) * scale)
            text += ebody[at:s] + ebody[s:s + ebody[s:e].index('(') + 1] + ', '.join(args) + ')'
            at = e
        text += ebody[at:]
        etr.last = False
        effect[name] = etr.script(text)
        missing |= set(etr.missing)
    U.EFFECT_CONDS = ()
    os.makedirs(wdir, exist_ok=True)
    end = [acmd.Command(acmd.END)]
    for fn, sc in (('game', game), ('effect', effect), ('sound', {})):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, end) for n in FLASH_MOTIONS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FLASH_MOTIONS))
    return 'flash: %s; left out %s %s; effects not in his bank: %s' % (
        ', '.join(n for n in FLASH_MOTIONS if n in game), gtr.skipped, etr.skipped, ', '.join(sorted(missing)) or '-')


def flare1_scripts(a, wdir):
    """the flare1 article's scripts: Ultimate's edge_flare1 Fly (its 4 hitboxes, the beam), Hit (the beam left,
    edge_shadowflare_beam_hit), End (the beam left); `orbit`: edge_flare2 Fly's attack (7 damage, 50 degrees, rehit
    45, fighters) as ids 0-4, Part i each (every orb its own hit record, as Ultimate's own objects), at the bone's
    origin: flare1.c places them (AttackModule(0x1, ...)) and plays the orbs' effects itself"""
    ids = effect_ids()
    gtr, etr = U.Translator({}), U.EffectTranslator({}, ids, {})
    U.EFFECT_CONDS = (U.LR_LEFT,)
    src = lambda d, n: U.functions(open(os.path.join(a.dump, d, n + '.txt')).read())  # noqa: E731
    fly, hit, end = src('edge_flare1', 'Fly'), src('edge_flare1', 'Hit'), src('edge_flare1', 'End')
    game, effect, missing = {}, {}, set()
    game['fly'] = gtr.script(fns_body(fly, 'game_fly'))
    for name, fns in (('fly', fly), ('hit', hit), ('end', end)):
        etr.last = False
        effect[name] = etr.script(fns_body(fns, 'effect_' + name))
        missing |= set(etr.missing)
    atk = _calls(fns_body(src('edge_flare2', 'Fly'), 'game_fly'), 'ATTACK')
    assert len(atk) == 1, len(atk)
    orbs = []
    for i in range(5):
        args = list(atk[0][2])
        args[1] = args[2] = str(i)
        orbs.append('macros::ATTACK(%s);' % ', '.join(args))
    game['orbit'] = gtr.script('if macros::is_excute(agent) {\n%s\n}\n' % '\n'.join(orbs))
    U.EFFECT_CONDS = ()
    os.makedirs(wdir, exist_ok=True)
    stop = [acmd.Command(acmd.END)]
    for fn, sc in (('game', game), ('effect', effect), ('sound', {})):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, stop) for n in FLARE1_MOTIONS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FLARE1_MOTIONS))
    return 'flare1: %s; left out %s %s; effects not in his bank: %s' % (
        ', '.join(sorted(set(game) | set(effect))), gtr.skipped, etr.skipped, ', '.join(sorted(missing)) or '-')


def acmd_ext_args():
    """tools/acmd_ext_cave.py's words, last: its hook at 0x04B79000 (position_vars_cave's var_entry) is undone by a
    later position_vars_cave (Hero fix 79 re-applied it: every 0x0F0003xx variable read 0 since), and flare1.c needs
    its SLOTn_SHARED_k variables (docs/native-notes.md)"""
    out = subprocess.run([sys.executable, os.path.join(HERE, 'acmd_ext_cave.py')], capture_output=True, text=True,
                         check=True).stdout.split()
    assert any(w.upper().startswith('0X04B79000=') for w in out), 'acmd_ext_cave: no var_entry hook'
    return out


def fns_body(fns, name):
    return fns[name]


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
    print(compile_msc(os.path.join(EDGE, 'edge.c'), os.path.join(msc, 'edge.mscsb')))
    compile_msc(os.path.join(EDGE, 'weapons/fire.c'), os.path.join(msc, 'fire/fire.mscsb'))
    print(fire_scripts(a, os.path.join(fighter, 'script/animcmd/weapon/fire')))
    compile_msc(os.path.join(EDGE, 'weapons/flash.c'), os.path.join(msc, 'flash/flash.mscsb'))
    print(flash_scripts(a, os.path.join(fighter, 'script/animcmd/weapon/flash')))
    print(compile_msc(os.path.join(EDGE, 'weapons/flare1.c'), os.path.join(msc, 'flare1/flare1.mscsb')))
    print(flare1_scripts(a, os.path.join(fighter, 'script/animcmd/weapon/flare1')))
    for name in PLACEHOLDERS:
        os.makedirs(os.path.join(msc, name), exist_ok=True)
        shutil.copy(os.path.join(a.zelda, 'script/msc/dein/dein.mscsb'), os.path.join(msc, name, name + '.mscsb'))
        shutil.copytree(os.path.join(a.zelda, 'script/animcmd/weapon/dein'),
                        os.path.join(fighter, 'script/animcmd/weapon', name), dirs_exist_ok=True)

    if a.rpx:
        import kind_expand
        import weapon_expand
        import edge_counter_cave
        import effect_heap_patch
        edge_counter_cave.check_base(a.rpx)
        effect_heap_patch.check_base(a.rpx)
        os.makedirs(os.path.join(a.out, 'code'), exist_ok=True)
        run(os.path.join(HERE, 'rpx_patch.py'), a.rpx, os.path.join(a.out, 'code/cross_f.rpx'),
            *kind_expand.args(kind_expand.build()[0]), *weapon_expand.args(weapon_expand.build()[0]),
            *edge_counter_cave.args(), *effect_heap_patch.args(), *acmd_ext_args())
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
