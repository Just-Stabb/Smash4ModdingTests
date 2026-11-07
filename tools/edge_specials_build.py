#!/usr/bin/env python3
"""Sephiroth's specials (fighters/edge/specials.md): his scripts, MSC, new articles and executable.

  python3 tools/edge_specials_build.py DUMP EDGE ZELDA ZELDA_UM VL MODEL OUT [--rpx IN.rpx]
                                       [--bank DIR] [--motions DIR] [--sound DIR]

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
  MiB: his bank ran it out, test 61 / 62) + tools/position_vars_cave.py again (its words, not its relocation moves:
  IN must have it already; test 96's stage-collision write, q 6 of the hit / status variables) + tools/acmd_ext_cave.py last (its var_entry hook; Shadow Flare's shared
  slot variables); re-applying them over an executable that has them gives it back, so IN
  can be the last test's;
- --bank: effect/edge/edge.010d0000.{ptcl,efc} from DIR/zelda.010d0000.* (tools/vfxb_to_ptcl.py);
- --motions: motion/body/main.pac from DIR/motion/body (tools/ultimate_fighter.py motions --add);
- --sound: DIR = tools/ultimate_sound.py's OUT (sound_ids.json): the body's sound / expression scripts translated from
  Ultimate's (ultimate_acmd.py --sound-ids --expressions, SOUND_CONDS) and the fire / flash / flare1 articles' sound
  scripts (without it they stay as before: the base's sound / expression scripts, the articles' empty).
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
# the flash: per tier its frame-0 script and its finisher (flash.c changes to 6 + tier at frame 15: dein has no
# animation, so the article's script never passes frame 0); extra_kinds.json "motions": 12
FLASH_MOTIONS = ('attacknohit', 'attack0', 'attack1', 'attack2', 'attack3', 'attack4',
                 'finishnohit', 'finish0', 'finish1', 'finish2', 'finish3', 'finish4')
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
                  '--translate', os.path.join(EDGE, 'specials_acmd.json'), *sound_args(a))
        log += run(os.path.join(HERE, 'effect_variants.py'), 'apply', os.path.join(tmp, 'effect.bin'), ids,
                   os.path.join(out, 'effect.bin'))
        for fn in ('sound.bin', 'expression.bin'):
            shutil.copy(os.path.join(tmp, fn), os.path.join(out, fn))
    game = acmd.ACMDFile.load(os.path.join(out, 'game.bin'))
    for name in EMPTY_GAME:
        game.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
    effect = acmd.ACMDFile.load(os.path.join(out, 'effect.bin'))
    if SNAKE_FAIR:
        glow = next(c for sc in effect.scripts.values() for c in sc if c.name == 'Sword_Glow')
        msg, hit = snake_fair_scripts(game, effect)
        log += msg + snake_hi3_scripts(game, effect)
        log += snake_article_scripts(fighter, hit, glow) + '\n'
        log += fill_scripts(fighter, hit) + '\n'
    log += octaslash_loop_scripts(game, effect)
    game.save(os.path.join(out, 'game.bin'))
    effect.save(os.path.join(out, 'effect.bin'))
    if a.sound:
        log += sound_fixes(os.path.join(out, 'sound.bin'), sound_ids(a))
    return log


# ---- held forward air: the extending sword (fighters/edge/snake_fair.md; MSC tools/edge_snake_msc.py). Test 79 drew it
# with 15 joints of his own model posed from MSC and the game crashed loading him (port_check C6); since test 82 it is
# drawn by articles: `snake` (a run, up to 12) and `snaketip` (the point, with the catch hitbox and the trail)
SNAKE_FAIR = True
SNAKE_VAR = 0x0F000317     # VAR_23: 0 the normal move, 1 held (extending / retracting), 2 the end hit
SNAKE_SWORD = 0x18         # joint 24, LHaveN (the sword in his hand)
SNAKE_ARTICLES = ('snake', 'snaketip')
TRAIL_HALF = 1.5            # the point's trail: half its width
SNAKE_MOTION = 0xEF3E3778  # the light arrow's one motion (their base kind's), the articles' motion 0


# --sound: his sound / expression scripts from Ultimate's (tools/ultimate_sound.py's sound_ids.json, the banks built
# on his slot's). In the sound scripts the down smash's floor hit and Scintilla's counter are taken as true (Ultimate's
# status sets them: the smash is grounded, the counter is the move's point; a whiff gets the counter's sounds); his
# One-Winged Angel flag and Scintilla's FLAG_VOICE as false (the form isn't ported; the stance's own voice off, the
# counter's on)
SOUND_CONDS = ('FIGHTER_EDGE_STATUS_ATTACK_LW4_WORK_FLAG_IS_HIT_FLOOR', 'FIGHTER_EDGE_STATUS_SPECIAL_LW_FLAG_IS_HIT_SHIELD')


def sound_args(a):
    if not a.sound:
        return []
    out = ['--sound-ids', os.path.join(a.sound, 'sound_ids.json'), '--expressions']
    for c in SOUND_CONDS:
        out += ['--sound-cond', c]
    return out


def sound_ids(a):
    """Ultimate sound name -> Smash 4 id: his banks' (--sound) and the common ones"""
    smap = json.load(open(os.path.join(ROOT, 'reference/ultimate_sound_map.json')))
    ids = {k: v for k, (v, _c) in smap['common_se'].items()}
    ids.update({k: v for k, v in json.load(open(os.path.join(a.sound, 'sound_ids.json'))).items()
                if not k.startswith('_')})
    return ids


def sound_fixes(path, ids):
    """forward air: the dump's sound script lost its branches (`if WINGED { 9: f02, winged_landing02 } 12: voice
    else { 0: f02 }`; Ultimate plays f02 at 9 in both, as his other winged / plain pairs): f01 at 2, f02 at 9, the
    voice at 12, the plain branch's"""
    f = acmd.ACMDFile.load(path)
    f.scripts[acmd.crc('attackairf')] = [
        U.cmd('FRAME', 2), U.cmd('Sound_Effect', ids['se_edge_attackair_f01']),
        U.cmd('FRAME', 9), U.cmd('Sound_Effect', ids['se_edge_attackair_f02']),
        U.cmd('FRAME', 12), U.cmd('Low_Voice_Clip', ids['seq_edge_rnd_attack_hard']), acmd.Command(acmd.END)]
    f.save(path)
    return 'attackairf sound: f01 at 2, f02 at 9, the voice at 12 (the dump lost its branches)\n'


def article_sound(a, ids, dump_dir, fname, fn):
    """an article's sound script from Ultimate's (dump_dir/fname's fn); [END] without --sound"""
    if not a.sound:
        return [acmd.Command(acmd.END)]
    st = U.SoundTranslator(ids)
    body = U.functions(open(os.path.join(a.dump, dump_dir, fname + '.txt')).read())[fn]
    out = st.script(U.fold_tests(body))
    assert not st.missing, st.missing
    return out


def _set(c, **kv):
    """a copy of command c with the named parameters changed"""
    syn = acmd.INFO[c.ident]['syntax']
    q = acmd.Command(c.ident, list(c.params))
    for k, v in kv.items():
        q.params[syn.index(k)] = v
    return q


def _when(value, body, var=SNAKE_VAR):
    """Float_Var_Compare(var == value) True { body }"""
    return [U.cmd('Float_Var_Compare', var, 0, float(value)), U.cmd('True', 2 + U.words(body))] + body


PHANTOM_HAND_FLASH = 0x3100016   # Zelda's purple flash on her hand (bone 0x7DA) as the Phantom attacks
# the Phantom's effects with endless emitters (vanilla zelda.010d0000.ptcl: one_time 0), PtcZeldaPhantomHold's two
# burst emitters' particles living 0x7FFFFFFF frames: Hold (its charge), Max (full charge), Line (its attack's)
PHANTOM_CHARGE = (0x3100017, 0x3100018)
PHANTOM_ENDLESS = PHANTOM_CHARGE + (0x310001E,)
EFFECT_STARTS = ('Graphic_Effect', 'Graphic_Effect2', 'Graphic_Effect3', 'Graphic_Effect4', 'External_Graphic')


def phantom_hand_flash(path):
    """the Phantom's attack effect scripts without Zelda's release flash on her hand (Graphic_Effect4 0x3100016 on
    bone 0x7DA): vanilla ends it with her release status; Sephiroth sends it from any status (tests 103 on), so it
    stayed on his hand (test 117, the user: "Sephiroth permanently has a purple effect on his hand")"""
    eff = acmd.ACMDFile.load(path)
    n = 0
    ended = 0
    for crc, cmds in eff.scripts.items():
        # both forms: Graphic_Effect4 (test 117) and the following External_Graphic on bone 2010 (0x7DA, the hand; test
        # 144, the user: "The purple aura stays attached to Sephiroth's arm permanently" after a Phantom release)
        keep = [c for c in cmds if not (c.name in ('Graphic_Effect4', 'External_Graphic') and c.params[0] == PHANTOM_HAND_FLASH)]
        n += len(cmds) - len(keep)
        # the endless ones (PHANTOM_ENDLESS) off at the start of every script but the charge's own (those that start
        # Hold / Max): its attack, break and end, so they never outlive the charge (multi-instance bugs v1, the user:
        # "still keeps the purple phantom release glow on his hand permanently"; weapons/phantom.c ph_fx_off ends
        # them at every status change and removal too)
        starts = {c.params[0] for c in keep if c.name in EFFECT_STARTS and c.params}
        if not starts & set(PHANTOM_CHARGE):
            keep = [U.cmd('Terminate_Graphic_Effect', fx, 1, 1) for fx in PHANTOM_ENDLESS] + keep
            ended += 1
        eff.scripts[crc] = keep
    assert n, 'phantom effect.bin: no hand flash found'
    eff.save(path)
    return 'phantom: its hand flash (%d commands) taken out; its endless effects ended in %d scripts' % (n, ended)


# held Octaslash's loop (test 113, edge.c edge_hi_*): VAR_20 0 a plain pass, 1 the first pass held, 2 a looped pass
# (SpecialHi2 changed to again at frame 4 by the MSC, so the script runs past frames 0 - 3 at once)
OCTA_VAR = 0x0F000314
OCTA_HELD_ANGLE, OCTA_HELD_FKB = 40, 100   # held Octaslash's slashes (test 134)


def octaslash_loop_scripts(game, effect):
    """SpecialHi2: its 1st hit (frame 2) and start effects (frame 0) not on a looped pass (VAR_20 0 / 1 only), the end
    flash (frame 15) only on a plain pass (0): held, the MSC plays frames 4 - 15 (the 2nd hit to the one before
    SpecialHi2End's) again and again"""
    crc = acmd.crc('SpecialHi2')
    out = []
    n = 0
    for f, body in _frames(game.scripts[crc]):
        if f == 2.0:
            hits = [c for c in body if c.name.endswith('Hitbox')]
            rest = [c for c in body if not c.name.endswith('Hitbox')]
            assert hits and rest[0].name == 'WAIT', [c.name for c in body]
            n = len(hits)
            body = _when(0, hits, OCTA_VAR) + _when(1, hits, OCTA_VAR) + rest
        if f == 4.0:
            # held (VAR_20 1 / 2), the loop's hits: 0.14% each, no hitlag (tests 126 / 127), and since test 134 no
            # multi-hit: a fixed knockback away from him at 40 degrees, again at each slash (its rehit every 2 frames,
            # Ultimate's), just past his 2.4 a frame (the user: "make held Octaslash no longer multihit, just send away
            # from Sephiroth with a fixed knockback hitbox that reactivates on the same timing as each slash to send at a
            # 40 degree angle, just slightly more enough to send the opponent a bit away so that they can't be
            # chained"): FKB 100, KBG 100 -> ((1 + 100 / 2) x 1.4 + 18) = 89 knockback at weight 100 (2.7 a frame, 36
            # frames of hitstun); facing restriction 0, by position (Ultimate's LR_CHECK_POS: away from him either side).
            # Let go (0), Ultimate's 2.3 and its hitlag
            loop = []
            for c in body:
                if c.name.endswith('Hitbox'):
                    held = _set(c, Damage=0.14, Hitlag=0.0, Angle=OCTA_HELD_ANGLE, KBG=100, FKB=OCTA_HELD_FKB, BKB=0,
                                FacingRestrict=0)
                    loop += _when(0, [c], OCTA_VAR) + _when(1, [held], OCTA_VAR) + _when(2, [held], OCTA_VAR)
                else:
                    loop.append(c)
            body = loop
        out.append((f, body))
    assert n, 'SpecialHi2: no frame 2 hit'
    game.scripts[crc] = _join(out)
    eout = []
    for f, body in _frames(effect.scripts[crc]):
        body = [c for c in body if c.ident != acmd.END]
        if f == 0.0 and body:
            body = _when(0, body, OCTA_VAR) + _when(1, body, OCTA_VAR)
        elif f == 15.0 and body:
            body = _when(0, body, OCTA_VAR)
        eout.append((f, body))
    effect.scripts[crc] = _join(eout) + [acmd.Command(acmd.END)]
    # a shape made in Octaslash ends it (VAR_20 3, edge.c edge_tr_steps): its finisher's hits at angle 366 (toward the
    # hitbox, on his sword: into the shape; test 127, the user: "the finisher hit angle that sends towards him, inside
    # the shape"); else as they were
    for name in ('SpecialHi2End', 'SpecialAirHi2End'):
        ecrc = acmd.crc(name)
        out = []
        for c in game.scripts[ecrc]:
            if c.name.endswith('Hitbox'):
                out += (_when(0, [c], OCTA_VAR) + _when(1, [c], OCTA_VAR) + _when(2, [c], OCTA_VAR)
                        + _when(3, [_set(c, Angle=366)], OCTA_VAR))
            else:
                out.append(c)
        game.scripts[ecrc] = out
    return ('held Octaslash: SpecialHi2 1st hit (%d hitboxes) and start / end effects gated on VAR_20; its loop hits 0.14%%, '
            'angle %d FKB %d by position; the finisher 366 after a shape, no hitlag while held\n' % (n, OCTA_HELD_ANGLE, OCTA_HELD_FKB))


def _frames(cmds):
    """[(frame, [commands after that FRAME up to the next])], the commands before any FRAME at frame 0"""
    out, cur, f = [], [], 0.0
    for c in cmds:
        if c.name == 'FRAME':
            out.append((f, cur))
            f, cur = float(c.params[0]), []
            continue
        cur.append(c)
    out.append((f, cur))
    return out


def _join(parts):
    cmds = []
    for i, (f, body) in enumerate(parts):
        if i:
            cmds.append(U.cmd('FRAME', f))
        cmds += body
    return cmds


def snake_fair_scripts(game, effect):
    """AttackAirF: the normal hits and effects only when not held (VAR_23 0); held, nothing more since test 103 (tests
    79 - 102: an 11% end hit on frames 14 - 18 once the sword was back; the user: only up tilt keeps one). The point's
    catch and trail are its article's (snake_article_scripts); frame 13's hitbox is the template for its catch"""
    crc = acmd.crc('AttackAirF')
    parts = _frames(game.scripts[crc])
    hb13 = next(body for f, body in parts if f == 13.0)
    hits = [c for c in hb13 if c.name == 'Extended_Special_Hitbox']
    assert len(hits) == 4, [c.name for c in hb13]
    # held: no end hit since test 103 (the user: "I actually think only Up tilt should have the hilt hitbox now";
    # tests 79 - 102 had an 11% end hit on frames 14 - 18 once the sword was back)
    end = []
    out = []
    for f, body in parts:
        if f in (13.0, 15.0):
            body = _when(0, body)
        out.append((f, body))
    if not any(f == 14.0 for f, _b in out):
        raise SystemExit('AttackAirF: no frame 14')
    game.scripts[crc] = _join(out)
    eout = [(f, _when(0, body) if f == 13.0 else body) for f, body in _frames(effect.scripts[crc])]
    effect.scripts[crc] = _join(eout)
    return '\nheld forward air: no end hit; normal hits / effects only when tapped\n', hits[0]


def snake_hi3_scripts(game, effect):
    """AttackHi3 held (user, test 97: "make held Up tilt work the same way that held forward air does"; MSC
    edge_sn_move 1): the tapped move's hits (frames 17, 20, 23: the pull, the clean and late hits, with frame 20's
    head intangibility and 23's end of it) and its frame 16 / 20 effects only at VAR_23 0; held, the end hit on frames
    21 - 24 once the sword is back (the motion frozen at 20, the sword straight up, runs again from there): frame 20's
    four hitboxes (on his root, up the sword) at 11%, angle 42, KBG 40, each 6 bigger, after Hit_Log_Clear(-1); off
    at 25"""
    crc = acmd.crc('AttackHi3')
    parts = _frames(game.scripts[crc])
    frames = [f for f, _b in parts]
    for need in (17.0, 20.0, 23.0):
        if need not in frames:
            raise SystemExit('AttackHi3: no frame %g' % need)
    hb20 = next(body for f, body in parts if f == 20.0)
    hits = [c for c in hb20 if c.name.endswith('Hitbox')]
    assert len(hits) == 4, [c.name for c in hb20]
    # angle 42 (test 103, the user: "Please make the up tilt hilt hitbox a 42 degree angle"; tests 98 - 102: up tilt's
    # own 90 / 91)
    # each 6 bigger (test 105, the user: "the hilt hitbox is still not hitting. Maybe the hitbox could be a bit bigger";
    # tests 98 - 104: 2), out on frames 21 - 24 (was 21 - 22)
    end = [_set(c, Part=0, Damage=11.0, Angle=42, KBG=40, Size=float(c.params[8]) + 6.0, SFXLevel=1) for c in hits]
    out = []
    for f, body in parts:
        if f in (17.0, 20.0):
            body = _when(0, body)
        if f == 23.0:
            body = _when(0, body)
        out.append((f, body))
        if f == 20.0:
            out.append((21.0, _when(2, [U.cmd('Remove_All_Hitboxes'), U.cmd('Hit_Log_Clear', -1)] + end)))
        if f == 23.0:
            out.append((25.0, _when(2, [U.cmd('Remove_All_Hitboxes')])))
    assert 21.0 not in frames and 25.0 not in frames
    game.scripts[crc] = _join(out)
    eout = [(f, _when(0, body) if f in (16.0, 20.0) else body) for f, body in _frames(effect.scripts[crc])]
    effect.scripts[crc] = _join(eout)
    return 'held up tilt: end hit (%d hitboxes, frames 21 - 24); normal hits / effects only when tapped\n' % len(end)


def snake_article_scripts(fighter, hit_template, glow_template):
    """the articles' ACMD (script/animcmd/weapon/<article>/: motion.mtable the light arrow's one motion): the run's
    empty; the point's game script its 5% catch (on its root, the middle of the point: tools/edge_snake_articles.py,
    the point 3.48 long along +Z), its effect script his sword trail's textures (0x104 / 0x105) across the point (its
    local Y), swept along its path"""
    tip = _set(hit_template, ID=0, Part=0, Bone=0, Damage=5.0, Angle=361, KBG=0, FKB=0, BKB=20, Size=4.5,
               X=0.0, Y=0.0, Z=1.74, X2=0.0, Y2=0.0, Z2=1.74, Hitlag=1.0, SFXLevel=0)
    # the trail's two points across the point along its local Y only: the article is turned (-angle, 90, 0), so its Y
    # is across the blade in the screen plane whichever way it runs, its X is depth (test 83's X and Y both: a wide
    # diagonal ribbon, partly facing the camera)
    trail = _set(glow_template, Bone1=0, X1=0.0, Y1=-TRAIL_HALF, Z1=1.74, Bone2=0, X2=0.0, Y2=TRAIL_HALF, Z2=1.74,
                 Bone3=0, X=0.0, Y=0.0, Z=1.74, BlurLength=8)
    stop = [acmd.Command(acmd.END)]
    for name in SNAKE_ARTICLES + ('trail',):    # trail: the up special's line pieces (test 123), no scripts
        d = os.path.join(fighter, 'script/animcmd/weapon', name)
        os.makedirs(d, exist_ok=True)
        game = [tip, acmd.Command(acmd.END)] if name == 'snaketip' else stop
        effect = [trail, acmd.Command(acmd.END)] if name == 'snaketip' else stop
        for fn, sc in (('game', game), ('effect', effect), ('sound', stop)):
            acmd.ACMDFile({SNAKE_MOTION: sc}).save(os.path.join(d, fn + '.bin'))
        open(os.path.join(d, 'motion.mtable'), 'wb').write(SNAKE_MOTION.to_bytes(4, 'big'))
    return 'held forward air articles: %s, and trail (scripts)' % ', '.join(SNAKE_ARTICLES)


# the closed-shape hitbox (tests 125 / 126, weapons/fill.c from tools/edge_fill_msc.py): motion 0 its hitboxes off
# (2 - 7 too: dein has 8 motion slots, a copy keeps them all), 1 its hitbox (the script's frame 0: a dein copy has no
# animation, so its script never passes it, as the flash's): a sphere on each of its joints J0 - J4 (0x7D2 - 0x7D6,
# spread along the shape's long axis), the size by the article's VAR_0 (the shape's half width b's tier) and damage /
# knockback by VAR_1 (its size sqrt(a b)'s tier): "a hitbox slightly larger than the shape formed, the damage and
# knockback scaling with the size of the shape". Angle 80, one hit log (one article) so a fighter is hit once
FILL_MOTIONS = ('fillnone', 'fillhit', 'fillnone2', 'fillnone3', 'fillnone4', 'fillnone5', 'fillnone6', 'fillnone7')
FILL_SIZES = (6.0, 9.5, 14.0, 19.5, 26.0)                                             # b up to 5 / 8 / 12 / 17 / more
# (damage, BKB, KBG) by sqrt(a b) up to 25 / 40 / 60 / 95 / more (edge_fill_msc DAMAGE_TIERS). Test 141, the user: "make
# shapes minimum damage lower and maximum damage higher with the same amount of knockback growth": 3 - 25% (6 - 18%
# before), KBG / BKB as they were
# Test 142, the user: "return the bkb and kbg values to what they were before and make damage affected the most", their
# choice: BKB 60 / KBG 100 (the old top tier) for every size, so only damage scales with it (tests 125 - 141: BKB 40 - 60,
# KBG 60 - 100 by tier)
FILL_DAMAGE = ((3.0, 60, 100), (7.0, 60, 100), (12.0, 60, 100), (18.0, 60, 100), (25.0, 60, 100))
FILL_VAR_SIZE, FILL_VAR_DAMAGE = 0x0F000300, 0x0F000301


def fill_scripts(fighter, hit_template):
    d = os.path.join(fighter, 'script/animcmd/weapon/fill')
    os.makedirs(d, exist_ok=True)
    game, stop = {}, {}
    hit = []
    for di, (dmg, bkb, kbg) in enumerate(FILL_DAMAGE):
        inner = []
        for si, size in enumerate(FILL_SIZES):
            boxes = [_set(hit_template, ID=k, Part=0, Bone=0x7D2 + k, Damage=dmg, Angle=80, KBG=kbg, FKB=0, BKB=bkb,
                          Size=size, X=0.0, Y=0.0, Z=0.0, X2=0.0, Y2=0.0, Z2=0.0, Hitlag=1.0, SFXLevel=1,
                          ShieldDamage=0,
                          # test 139, the user: "make shapes always win clank scenarios": no clank (Clang 0: it doesn't
                          # meet other hitboxes, so nothing cancels it), no rebound; it was already neither reflectable
                          # nor absorbable
                          Clang=0, Rebound=0, Reflectable=0, Absorbable=0) for k in range(5)]
            inner += _when(si + 1, boxes, FILL_VAR_SIZE)
        hit += _when(di + 1, inner, FILL_VAR_DAMAGE)
    for i, name in enumerate(FILL_MOTIONS):
        crc = acmd.crc(name)
        stop[crc] = [acmd.Command(acmd.END)]
        game[crc] = (hit if i == 1 else [U.cmd('Remove_All_Hitboxes')]) + [acmd.Command(acmd.END)]
    acmd.ACMDFile(game).save(os.path.join(d, 'game.bin'))
    for fn in ('effect', 'sound'):
        acmd.ACMDFile(dict(stop)).save(os.path.join(d, fn + '.bin'))
    open(os.path.join(d, 'motion.mtable'), 'wb').write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FILL_MOTIONS))
    return 'fill: %d motions, the hit %d hitboxes (5 sizes x 5 damages x 5 spheres)' % (len(FILL_MOTIONS), 125)


def fire_scripts(a, wdir):
    """the fire article's game / effect scripts from Ultimate's edge_fire ones (hitboxes and effects
    on its bone 0); sound: Ultimate's edge_fire ones with --sound (the flight's loop, the bursts' PLAY_SE_REMAIN)"""
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
    sound = {}
    if a.sound:
        ids = sound_ids(a)
        for fname in sorted(os.listdir(src_dir)):
            name = fname[:-4].lower()
            if 'sound_' + name in U.functions(open(os.path.join(src_dir, fname)).read()):
                sound[name] = article_sound(a, ids, 'edge_fire', fname[:-4], 'sound_' + name)
    for fn, sc in (('game', game), ('effect', effect), ('sound', sound)):          # dein's files
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
    """the flash article's game / effect scripts: Ultimate's edge_flash Attack per tier (FLASH_MOTIONS), frame 0 in
    attack*, frame 15's finisher in finish* (flash.c plays the rest: the script never passes frame 0). Game: the
    whiff's hitboxes (FLAG_HIT off) or the counter's id 0 -> id 1 at the tier's p (ATTACK_SET_LERP +
    ATK_LERP_RATIO); its frame-16 notify (removal) is flash.c's. Effect: the effects scaled as its exec (31950)
    scales the last one made each frame (EFFECT_ID): every one but the first puff (replaced by edge_senkou_hold
    in the same frame) at effect_scale_no_hit 0.65 / 1.2 + 0.8 p. Sound (--sound): Attack's in every tier's attack*"""
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
        game[name] = gtr.script('if macros::is_excute(agent) {\n%s\n}\n' % f0)
        fin = 'finish' + name[len('attack'):]
        game[fin] = gtr.script('if macros::is_excute(agent) {\nAttackModule::clear_all(agent.module_accessor);\n%s\n}\n'
                               % f15)
        # frame 0's effects only (up to the first wait): flash.c plays the later ones
        text, at = '', 0
        for s, e, args in sorted(efx):
            if s != first:
                args = list(args)
                args[9] = '%.3f' % (float(args[9]) * scale)
            text += ebody[at:s] + ebody[s:s + ebody[s:e].index('(') + 1] + ', '.join(args) + ')'
            at = e
        text += ebody[at:]
        text = text[:text.index('wait(agent.lua_state_agent')]
        etr.last = False
        effect[name] = etr.script(text)
        missing |= set(etr.missing)
    U.EFFECT_CONDS = ()
    os.makedirs(wdir, exist_ok=True)
    end = [acmd.Command(acmd.END)]
    sound = {}
    if a.sound:                     # Attack's frame-0 sound (PLAY_SE_REMAIN) in every tier's frame-0 script
        snd = article_sound(a, sound_ids(a), 'edge_flash', 'Attack', 'sound_attack')
        sound = {n: snd for n in FLASH_MOTIONS if n.startswith('attack')}
    for fn, sc in (('game', game), ('effect', effect), ('sound', sound)):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, end) for n in FLASH_MOTIONS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FLASH_MOTIONS))
    return 'flash: %s; left out %s %s; effects not in his bank: %s' % (
        ', '.join(n for n in FLASH_MOTIONS if n in game), gtr.skipped, etr.skipped, ', '.join(sorted(missing)) or '-')


FLARE1_CLEAR_VAR = 0x0F000314   # VAR_20 of flare1: hit records to clear when `orbit` runs (flare1.c fl_hitboxes)


def flare1_scripts(a, wdir):
    """the flare1 article's scripts: Ultimate's edge_flare1 Fly (its 4 hitboxes, the beam), Hit (the beam left,
    edge_shadowflare_beam_hit), End (the beam left); `orbit`: edge_flare2 Fly's attack (7 damage, 50 degrees, rehit
    45, fighters) as ids 0-4 at the bone's origin: flare1.c places them (AttackModule(0x1, ...)) and plays the orbs'
    effects itself. Ultimate's orbs are objects of their own (a hit record each); a dein copy has 7 hitbox ids but
    only 2 Parts (dein's set-up 0x032107B4: Part 2+ wrote past the hit records and crashed on the hit, bisect 70),
    so orb i is Part i % 2 and `orbit` starts with Hit_Log_Clear on the Parts flare1.c asks for in VAR_20 (1 Part 0,
    2 Part 1, 3 both): an orb that starts (its appear done), strikes or explodes gets a new record, as Ultimate's
    new status does"""
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
    # Fly's beam (edge_shadowflare_beam, EFFECT_FOLLOW on top at frame 0): its particles stay where they're born, and
    # on frame 0 the top joint is still at Din's creation point (the joint's matrix lags the move flare1.c makes in
    # FLY's main): the beam lay on the floor (tests 72 - 74, user: "Side special's initial hit effect still seems to
    # spawn too low"). flare1.c lays it itself at the moved place (fl_fly_main), so Fly's script has none
    effect['fly'] = [c for c in effect['fly'] if not (c.params and c.params[0] == ids['edge_shadowflare_beam'])]
    atk = _calls(fns_body(src('edge_flare2', 'Fly'), 'game_fly'), 'ATTACK')
    assert len(atk) == 1, len(atk)
    orbs = []
    for i in range(5):
        args = list(atk[0][2])
        args[1], args[2] = str(i), str(i % 2)
        orbs.append('macros::ATTACK(%s);' % ', '.join(args))
    clear = []
    for v, part in ((1, 0), (2, 1), (3, -1)):
        body = [U.cmd('Hit_Log_Clear', part)]
        clear += [U.cmd('Float_Var_Compare', FLARE1_CLEAR_VAR, 0, float(v)),
                  U.cmd('True', 2 + sum(acmd.INFO[c.ident]['size'] for c in body))] + body
    game['orbit'] = clear + gtr.script('if macros::is_excute(agent) {\n%s\n}\n' % '\n'.join(orbs))
    U.EFFECT_CONDS = ()
    os.makedirs(wdir, exist_ok=True)
    stop = [acmd.Command(acmd.END)]
    sound = {}
    if a.sound:     # the shot's (edge_flare1 Fly); the orbs' hum / strike (edge_flare2 Fly / Try) left out: flare1.c
        sound['fly'] = article_sound(a, sound_ids(a), 'edge_flare1', 'Fly', 'sound_fly')   # plays `orbit` for several events
    for fn, sc in (('game', game), ('effect', effect), ('sound', sound)):
        acmd.ACMDFile({acmd.crc(n): sc.get(n, stop) for n in FLARE1_MOTIONS}).save(os.path.join(wdir, fn + '.bin'))
    with open(os.path.join(wdir, 'motion.mtable'), 'wb') as f:
        f.write(b''.join(acmd.crc(n).to_bytes(4, 'big') for n in FLARE1_MOTIONS))
    return 'flare1: %s; left out %s %s; effects not in his bank: %s' % (
        ', '.join(sorted(set(game) | set(effect))), gtr.skipped, etr.skipped, ', '.join(sorted(missing)) or '-')


def position_vars_args(rpx):
    """tools/position_vars_cave.py's words again over IN, which has the cave already (its relocation moves are made
    once: left out), so a change to it reaches the build (test 96: GroundModule on another fighter, q 6 of the hit /
    status variables); acmd_ext_cave's var_entry hook goes on after it"""
    import rpx_patch
    out = subprocess.run([sys.executable, os.path.join(HERE, 'position_vars_cave.py')], capture_output=True,
                         text=True, check=True).stdout.split()
    words = [w for w in out if not w.startswith('reloc:')]
    hook = next(w for w in words if w.upper().startswith('0X02003750='))
    d, _o, _e, secs = rpx_patch.load(rpx)
    w = rpx_patch.read_u32(d, secs, 0x02003750)
    to = (0x02003750 + ((w & 0x3FFFFFC) - (0x4000000 if w & 0x2000000 else 0))) & 0xFFFFFFFF
    # IN has the cave when its input hook is a branch into it (where to moves when the cave's blocks are packed
    # differently: these words put the new layout in, hook included)
    assert w >> 26 == 18 and 0x037E0000 <= to < 0x04B80000, \
        '%s: no position_vars_cave (its input hook at 0x02003750)' % rpx
    return words


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
    ap.add_argument('--sound', help="tools/ultimate_sound.py's OUT (its sound_ids.json): his sound / expression "
                    "scripts and the articles' sound scripts from Ultimate's (without: the base's, as before)")
    ap.add_argument('--body-model', help='his built body model c00 (model.nud / .nut): the held forward air '
                    'articles\' models take the sword\'s material from it (tools/edge_snake_articles.py)')
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
    # Zelda's Phantom (article 2), Sephiroth's: her vanilla script with its tracking (test 106; weapons/phantom.c). Its
    # files load by its weapon kind's owner: Zelda's own kind read hers (fighter/zelda/), so since test 111 it's his
    # own kind 0x19B (extra_kinds.json "phantom": a copy of hers in his article 2), and its model, motion and ACMD
    # are hers copied into his folder
    compile_msc(os.path.join(EDGE, 'weapons/phantom.c'), os.path.join(msc, 'phantom/phantom.mscsb'))
    for sub in ('model/phantom', 'motion/phantom', 'script/animcmd/weapon/phantom'):
        shutil.copytree(os.path.join(a.zelda, sub), os.path.join(fighter, sub), dirs_exist_ok=True)
    print(phantom_hand_flash(os.path.join(fighter, 'script/animcmd/weapon/phantom/effect.bin')))
    print(flare1_scripts(a, os.path.join(fighter, 'script/animcmd/weapon/flare1')))
    if SNAKE_FAIR:                                  # the held forward air's articles: MSC and models
        import edge_snake_articles
        for name in SNAKE_ARTICLES:
            compile_msc(os.path.join(EDGE, 'weapons', name + '.c'), os.path.join(msc, name, name + '.mscsb'))
        import edge_trail_msc
        open(os.path.join(EDGE, 'weapons/trail.c'), 'w').write(edge_trail_msc.generate())
        compile_msc(os.path.join(EDGE, 'weapons/trail.c'), os.path.join(msc, 'trail/trail.mscsb'))
        print(edge_snake_articles.build_trail(os.path.join(a.zelda, 'model/lightingbowarrow/c00'), fighter))
        import edge_fill_msc
        open(os.path.join(EDGE, 'weapons/fill.c'), 'w').write(edge_fill_msc.generate())
        compile_msc(os.path.join(EDGE, 'weapons/fill.c'), os.path.join(msc, 'fill/fill.mscsb'))
        print(edge_snake_articles.build_fill(os.path.join(a.zelda, 'model/lightingbowarrow/c00'), fighter))
        if a.body_model:
            print(edge_snake_articles.build(os.path.join(a.edge, 'model/body/c00'), a.body_model,
                                            os.path.join(a.zelda, 'model/lightingbowarrow/c00'), fighter))
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
            *edge_counter_cave.args(), *effect_heap_patch.args(), *position_vars_args(a.rpx), *acmd_ext_args())
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
