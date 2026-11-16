#!/usr/bin/env python3
"""Byleth's moves (fighters/master/README.md): his held weapons' visibility, his specials' scripts and slots, his MSC,
his arrows (the copied Paralyzer shot, weapon kind 0x19E) and the vl motion bytes of every slot he plays.

  python3 tools/master_build.py vis DUMP ULT OUT.json
  python3 tools/master_build.py build DUMP ULT BODY MODEL BASE PKG [--sound DIR]

vis: fighters/master/weapon_vis.json for `ultimate_fighter.py motions --extra-vis` (port.json motions.extra_vis): for
every Ultimate body motion whose game script generates / removes / uses Areadbhar (SPEAR), Aymr (AXE) or Failnaught
(BOW), the frames that weapon is out: generated at g -> shown from g; removed at r -> hidden from r; named without being
generated (IS_EXIST_ARTICLE / change_motion: it was made by the motion before, Failnaught's shot after the charge) ->
shown from frame 0. The meshes are Ultimate's article models held rigidly on his hand (ultimate_fighter.py
SZEROSUIT_SLOTS: three of ZSS's mouth slots).

build (the plan's specials step, after the scripts step): on PKG/fighter/master (DUMP: lua2cpp_master; ULT: Ultimate's
fighter/master; BODY: the universal-mechanics body scripts (the base's); MODEL: his converted model/body/c00; BASE: ZSS's
vanilla fighter folder):
- the special slots: ZSS's scripts left in slots he doesn't play emptied (port_check B1), the air up special's tether
  (aircatch: her whip, article 2, generated / sent out / pulled back as her own AirCatch does it, at Sword of the
  Creator's frames), Aymr's armor;
- script/msc/master.mscsb from fighters/master/master.c (MASTER_* constants below: Ultimate's vl.prc values);
- the arrows: script/animcmd/weapon/paralyzer_bullet (her Paralyzer shot's eight motions: the uncharged ones Failnaught's
  arrow, the charged ones the max arrow), its params in his vl file (speed / life);
- the vl motion bytes (group 1) of every fighter-specific slot (0x211 on): Ultimate's cancel / intangible frames for the
  slot he plays, 0 for every other (ZSS's Flip Jump window 3-13, her Boost Kick's byte 5: Supamario Core Breaker v11).
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import acmd  # noqa: E402

MDIR = os.path.join(ROOT, 'fighters', 'master')
WEAPONS = {'SPEAR': 'master_spear', 'AXE': 'master_axe', 'BOW': 'master_bow'}
# the Sword of the Creator's whip (the `sword` article) is an article of its own since v6 (tools/master_whip.py: his copy
# of ZSS's whip, article 2): his body's sword follows Ultimate's own master_sword track, hidden while the article is out.
# (v5 stood the body's sword in for the missing article: WEAPONS 'SWORD' / ultimate_fighter.VIS_ALSO 'master_sword'.)
# articles whose own motion folder plays a body motion its game script doesn't generate / remove them in: out from
# the motion before (Failnaught's turn: v1-v4 hid the bow in SpecialNTurn while Ultimate's bow plays d00specialnturn)
ARTICLE_MOTIONS = {'bow': 'master_bow', 'axe': 'master_axe', 'spear': 'master_spear'}
# the body sword's own track where the whip shows on another timeline than Ultimate's article: the air up special's
# tether (ZSS's native whip, statuses 1 / 3: master_whip.py) is drawn from 17 (EXTEND) and taken away at 35, so the body
# sword shows before and after it (Ultimate: hidden 2 - 51, its article's start / back motions in the hand)
SWORD_VIS = {'d02specialairhi': [[0, 1], [17, 0], [35, 1]],
             # no whip slot left for these (ZSS's whip has 15 motion names, all his: master_whip.SLOTS): Win3 (the
             # result screen) and his Final Smash animations (the Final Smash is ZSS's: no sword article) keep the body
             # sword in hand where Ultimate whips the article (approximated)
             'j02win3': [[0, 1]], 'd04finalstart': [[0, 1]], 'd04finalairstart': [[0, 1]], 'd04finalend': [[0, 1]],
             'd04finalairend': [[0, 1]]}


# ---------------------------------------------------------------- the held weapons' visibility
def script_anims(ult):
    """{game script name (lower case, no game_): Ultimate animation name} from motion_list.bin"""
    import glob
    import ultimate_acmd as U
    mdir = os.path.join(ult, 'motion/body/c00')
    files = {U.hash40(os.path.basename(f)): os.path.basename(f)[:-7] for f in glob.glob(mdir + '/*.nuanmb')}
    out = {}
    for e in U.read_motion_list(os.path.join(mdir, 'motion_list.bin')):
        if not e['anims'] or e['anims'][0] not in files:
            continue
        for h in (e['game'],) + tuple(e['scripts']):
            out[h] = files[e['anims'][0]]
    return out


def weapon_frames(body):
    """{visibility name: [[frame, 0 / 1], ...]} for one game script's body"""
    frame = 0.0
    keys = {}
    seen = set()
    for m in re.finditer(r'frame\(agent\.lua_state_agent, ([\d.]+)\)|wait\(agent\.lua_state_agent, ([\d.]+)\)|'
                         r'(generate_article|remove_exist|change_motion|IS_EXIST_ARTICLE|set_flag|shoot_exist)'
                         r'[^;]*?GENERATE_ARTICLE_(SPEAR|AXE|BOW)\b', body):
        if m.group(1):
            frame = max(frame, float(m.group(1)))
            continue
        if m.group(2):
            frame += float(m.group(2))
            continue
        name = WEAPONS[m.group(4)]
        k = keys.setdefault(name, [])
        if m.group(3) == 'generate_article':
            k.append([int(frame), 1])
        elif m.group(3) == 'remove_exist':
            if name not in seen and not k:
                k.append([0, 1])                 # out since the motion before
            k.append([int(frame), 0])
        elif not k:
            k.append([0, 1])                     # used: out since the motion before
        seen.add(name)
    return keys


def cmd_vis(a):
    import ultimate_acmd as U
    anims = script_anims(a.ult)
    out = {}
    sdir = os.path.join(a.dump, 'master')
    for fn in sorted(os.listdir(sdir)):
        fns = U.functions(open(os.path.join(sdir, fn)).read())
        for name, body in fns.items():
            if not name.startswith('game_'):
                continue
            keys = weapon_frames(body)
            anim = anims.get(U.hash40(name))
            if keys and anim:
                cur = out.setdefault(anim, {})
                for k, v in keys.items():
                    # by frame, a frame's keys in script order (sorted pairs put [f, 0] before [f, 1])
                    cur[k] = sorted(cur.get(k, []) + v, key=lambda kv: kv[0])
    for anim, keys in SWORD_VIS.items():
        out.setdefault(anim, {})['master_sword'] = keys
    for art, vname in ARTICLE_MOTIONS.items():
        mdir = os.path.join(a.ult, 'motion', art, 'c00')
        if not os.path.isdir(mdir):
            continue
        for f in sorted(os.listdir(mdir)):
            anim = f[:-7]
            if f.endswith('.nuanmb') and vname not in out.get(anim, {}) and not anim.startswith(('d04', 'j02')):
                out.setdefault(anim, {})[vname] = [[0, 1]]
    json.dump(dict(_about='tools/master_build.py vis: Ultimate animation -> {weapon visibility: [[frame, shown]]} '
                          '(ultimate_fighter.py motions --extra-vis)', **out), open(a.out, 'w'), indent=1, sort_keys=True)
    print('%d motions show a held weapon: %s' % (len(out), ', '.join(
        '%s %s' % (k, '/'.join(sorted(n[7:] for n in v))) for k, v in sorted(out.items()))))


# ---------------------------------------------------------------- the MSC
# master.c's constants: Ultimate's vl.prc (param_special_*) and the frames of his scripts; (mine) where neither has it
CONSTS = dict(
    MASTER_ARROW1='0x6', MASTER_ARROW2='0x7',          # his article list: ZSS's 6, then the arrows (extra_kinds.json)
    # Failnaught: param_special_n cancel_start_frame / cancel_end_frame; SpecialNStart's ENABLE_TURN (28 - 44) and
    # CAN_SHOOT (45); the turn's stick (mine: Ultimate's common turn threshold isn't read)
    MASTER_N_CANCEL_START='20.0f', MASTER_N_CANCEL_END='65.0f', MASTER_N_TURN_START='28.0f', MASTER_N_TURN_END='44.0f',
    MASTER_N_TURN_STICK='0.5f', MASTER_N_CAN_SHOOT='45.0f',
    # Areadbhar: param_special_s sp_s_speed_x, sp_s_speed_x_air_mul, sp_s_brake_x / _air, sp_s_atk_end_speed_x_mul,
    # sp_s_atk_end_brake_x / _air_x, landing_speed_x_mul, landing_brake_x; SpecialSF's SPEED_F_REQUEST (2) and
    # SPEED_CHANGE_ATK_END_REQUEST (14)
    MASTER_S_SPEED='3.0f', MASTER_S_AIR_MUL='0.6f', MASTER_S_BRAKE='0.34f', MASTER_S_BRAKE_AIR='0.22f',
    MASTER_S_SPEED_FRAME='2.0f', MASTER_S_END_FRAME='14.0f', MASTER_S_END_MUL='1.0f', MASTER_S_END_BRAKE='0.07f',
    MASTER_S_END_BRAKE_AIR='0.008f', MASTER_S_LANDING_MUL='0.9f', MASTER_S_LANDING_BRAKE='0.03f',
    # Sword of the Creator: param_special_hi start_speed_y_air, wall_hit_max, jump_speed_x / _y; SpecialAirHi's hits
    # (16 - 25) and the sword back (27); the hit's pull: master.c master_hi_pull (rewind_speed 4.1 toward the tip,
    # tools/master_whip.py tips)
    MASTER_HI_START_Y='1.4f', MASTER_HI_HIT_START='16.0f', MASTER_HI_HIT_END='25.0f', MASTER_HI_WALL_END='27.0f',
    MASTER_HI_WALL_MAX='3', MASTER_HI_JUMP_X='0.9f',
    MASTER_HI_JUMP_Y='2.6f',
    # Aymr: param_special_lw super_armor_damage_max; SpecialLw's START / END_SUPER_ARMOR (34 / 64), INHERIT_LANDING_1's
    # end (51), INHERIT_LANDING_2 (65 - 117)
    MASTER_LW_ARMOR='30.0f', MASTER_LW_ARMOR_START='34.0f', MASTER_LW_ARMOR_END='64.0f', MASTER_LW_INHERIT1_END='51.0f',
    MASTER_LW_INHERIT2_START='65.0f', MASTER_LW_INHERIT2_END='117.0f')


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def compile_msc(src, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = open(src).read()
    for k in sorted(CONSTS, key=len, reverse=True):
        text = text.replace(k, CONSTS[k])
    left = sorted(set(re.findall(r'\bMASTER_[A-Z0-9_]+\b', text)))
    assert not left, 'master.c: constants without a value: %s' % left
    with tempfile.NamedTemporaryFile('w', suffix='.c', delete=False) as f:
        f.write(text)
    try:
        out = run(os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'), f.name, '-o', out_path)
    finally:
        os.unlink(f.name)
    assert os.path.getsize(out_path) > 0
    return out


# ---------------------------------------------------------------- the body scripts
# the slots his statuses play (fighters/master/master.c) and the Ultimate motion of each (the vl bytes); every other
# fighter-specific slot up to the Final Smash's is ZSS's and emptied (scripts) / zeroed (vl bytes 2-5)
PLAYED = {0x211: 'SpecialNStart', 0x212: 'SpecialNTurn', 0x215: 'SpecialN', 0x219: 'SpecialNMax',
          0x21D: 'SpecialAirNStart', 0x21E: 'SpecialAirNTurn', 0x221: 'SpecialAirN', 0x225: 'SpecialAirNMax',
          0x229: 'SpecialNCancel', 0x22A: 'SpecialAirNCancel',
          0x22D: 'SpecialSStart', 0x22E: 'SpecialSF', 0x22F: 'SpecialSLanding', 0x231: 'SpecialAirSStart',
          0x232: 'SpecialAirSF',
          0x239: 'SpecialHi', 0x23A: 'SpecialAirHiHit', 0x23B: 'SpecialAirHiOvertake', 0x23C: 'SpecialAirHiWallJump',
          0x241: 'SpecialLw', 0x245: 'SpecialAirLw', 0x255: 'SpecialLwLanding1', 0x259: 'SpecialLwLanding2'}
FIRST_OWN, FINAL = 0x211, (0x25D, 0x25E)
ZSS_SE_BANK = 0x1B                                 # her se ids 0x1B0000 + n           # ZSS's Final Smash slots: hers, kept (user)
END = None


def end():
    return [acmd.Command(acmd.END)]


def ult_script(U, path, name):
    p = os.path.join(path)
    if not os.path.exists(p):
        return None
    return U.functions(open(p).read()).get(name)


def body_fix(a, fighter):
    """the special slots: ZSS's leftovers emptied, the tether's whip, the overtake's hit, Aymr's axe hitbox; ZSS's
    Final Smash scripts as hers"""
    import ultimate_acmd as U
    d = os.path.join(fighter, 'script/animcmd/body')
    mt = open(os.path.join(d, 'motion.mtable'), 'rb').read()
    h = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    van = os.path.join(a.base, 'script/animcmd/body')
    vmt = open(os.path.join(van, 'motion.mtable'), 'rb').read()
    vh = list(struct.unpack('>%dI' % (len(vmt) // 4), vmt))
    joints = U.joint_ids(a.model)
    log = []
    files = {fn: acmd.ACMDFile.load(os.path.join(d, fn + '.bin')) for fn in ('game', 'effect', 'sound', 'expression')}
    vfiles = {fn: acmd.ACMDFile.load(os.path.join(van, fn + '.bin')) for fn in files}
    same = lambda x, y: [str(c) for c in x] == [str(c) for c in y]          # noqa: E731
    played = set(PLAYED)
    emptied = []
    for i in range(FIRST_OWN, len(h)):
        if i in FINAL or not h[i]:
            continue
        for fn, f in files.items():
            s = f.scripts.get(h[i])
            if s is None:
                continue
            leftover = h[i] == vh[i] and h[i] in vfiles[fn].scripts and same(s, vfiles[fn].scripts[h[i]])
            if (i not in played or leftover) and not same(s, end()):
                f.scripts[h[i]] = end()
                emptied.append('%s 0x%X' % (fn, i))
    log.append('ZSS leftovers emptied: %d (%s)' % (len(emptied), ', '.join(emptied)))
    # her scripts no motion names any more (the custom-move slots now his: specials_c2 ... specialhi_c3) and her
    # sub-scripts only they called: gone (port_check B1)
    live = set(x for x in h if x)
    refs = set()
    for f in files.values():
        for k, sc in f.scripts.items():
            if k in live:
                refs |= {int(p) for c in sc if c.name in ('CALL', 'JUMP') for p in c.params[:1]}
    gone = 0
    for f in files.values():
        for k in [k for k in f.scripts if k not in live and k not in refs]:
            del f.scripts[k]
            gone += 1
    log.append('scripts no motion plays (her custom moves\' and their sub-scripts): %d removed' % gone)
    # her own tones (her se bank's ids, 0x1B....) in her sound scripts left on motions Ultimate has no sound for (Turn,
    # Wait2, crawls, item swings, ...): out (his Ultimate scripts play none there); the common tones stay
    quiet = 0
    for k, sc in list(files['sound'].scripts.items()):
        v = vfiles['sound'].scripts.get(k)
        if v is None or not same(sc, v):
            continue
        keep = [c for c in sc if not (c.name.startswith(('Sound_Effect', 'Transient_Sound', 'Stop_Sound'))
                                      and c.params and int(c.params[0]) >> 16 == ZSS_SE_BANK)]
        if len(keep) != len(sc):
            if not [c for c in keep if c.name not in ('FRAME', 'WAIT') and c.ident != acmd.END]:
                keep = end()
            files['sound'].scripts[k] = keep
            quiet += 1
    log.append('her own tones out of %d of her sound scripts' % quiet)
    # her angled forward tilts play his one forward tilt (the translator's FALLBACK gives them its game script): its
    # effect / sound / expression too
    s3 = acmd.crc('attacks3')
    for n in ('attacks3hi', 'attacks3lw'):
        for fn in ('effect', 'sound', 'expression'):
            if s3 in files[fn].scripts:
                files[fn].scripts[acmd.crc(n)] = [acmd.Command(c.ident, list(c.params)) for c in files[fn].scripts[s3]]
    for i in FINAL:                                    # her Final Smash, as hers
        for fn, f in files.items():
            if vh[i] in vfiles[fn].scripts:
                f.scripts[vh[i]] = [acmd.Command(c.ident, list(c.params)) for c in vfiles[fn].scripts[vh[i]]]
    g = files['game'].scripts
    # the air Sword of the Creator: her whip (article 2: his copy, weapon kind 0x1A0, the sword since v6) out as her AirCatch does,
    # at the sword's frames (Ultimate's sword article EXTEND at 17, BACK at 27); her frame-0 flag (0x2100000D, 5 frames:
    # the common AirCatch's ground check, func_124)
    ac = acmd.crc('aircatch')
    # the whip hidden until it goes out (status 0 plays no motion of ours: her aircatch hides it so too); his body sword
    # shows until then (SWORD_VIS)
    whip = [U.cmd('GENERATE_ARTICLE', 2), U.cmd('Article_Visibility', 2, 0), U.cmd('ON_FLAG', 0x2100000D),
            U.cmd('FRAME', 5), U.cmd('OFF_FLAG', 0x2100000D),
            U.cmd('FRAME', 17), U.cmd('Article_Visibility', 2, 1), U.cmd('Set_Remote_Article_Action', 2, 1),
            U.cmd('FRAME', 27), U.cmd('Set_Remote_Article_Action2', 2, 3),
            U.cmd('FRAME', 35), U.cmd('Remove_Article', 2)] + end()
    if any(c.name == 'GENERATE_ARTICLE' for c in g[ac]):
        # this step's output already (the step run again on its build): the merges below are done
        for fn, f in files.items():
            f.save(os.path.join(d, fn + '.bin'))
        log.append('aircatch / overtake / Aymr: done already (this step ran on this build before)')
        return log
    merged = U.merge_flat(g[ac], whip)
    assert merged is not None, 'aircatch: a branching script'
    g[ac] = merged
    # the overtake: Ultimate throws the caught fighter (ATTACK_ABS CATCH / THROW / THROW_MEWTWO, ATK_HIT_ABS at frame 11);
    # here nothing is caught (the hit pulls, 0x15B): its CATCH numbers (the air target's: 6.5, 114 degrees, 65 / 65) as
    # a hitbox around him on frames 9 - 11
    tr = U.Translator(joints)
    hit = tr.script('frame(agent.lua_state_agent, 9.0); macros::ATTACK(agent, 0, 0, Hash40::new("top"), 6.5, 114, 65, 0, '
                    '65, 8.0, 0.0, 10.0, 3.0, None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_F, '
                    'false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_GA, '
                    '*COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, '
                    'Hash40::new("collision_attr_normal"), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_CUTUP, '
                    '*ATTACK_REGION_SWORD); frame(agent.lua_state_agent, 12.0); AttackModule::clear_all(agent.module_accessor);')
    ov = acmd.crc('specialairhiovertake')
    keep = [c for c in g[ov] if c.name not in ('Throw_Specifier', 'Throw_Applier', 'Throw_Specifier2')]
    g[ov] = U.merge_flat(keep, hit)
    # Aymr: the axe's hitbox (Ultimate's master_axe SpecialLw / SpecialAirLw: on the axe's haver, which follows his)
    for src, name in (('SpecialLw', 'speciallwstart'), ('SpecialAirLw', 'specialairlwstart')):
        body = ult_script(U, os.path.join(a.dump, 'master_axe', src + '.txt'), 'game_' + src.lower())
        if body is None:
            continue
        axe = Translator_script(U, joints, body)
        m = U.merge_flat(g[acmd.crc(name)], axe)
        assert m is not None
        g[acmd.crc(name)] = m
    for line in article_effects(a, fighter, files['effect'], joints, files['game']):
        log.append(line)
    import master_whip
    master_whip.body_scripts(files['game'], log.append)
    for fn, f in files.items():
        f.save(os.path.join(d, fn + '.bin'))
    log.append('aircatch: the whip at 0 / 17 / 27 / 35; overtake: a hitbox for the throw; Aymr: the axe\'s hitbox merged')
    return log


# the held weapons' own effect scripts (Ultimate plays them on the articles, which are baked into his body here):
# article -> (the fighter bone its root is linked to, {bone renamed in its scripts: new name}). The bow's top is the
# fighter's (its shot effects at (0, 9.8, 15) are his chest); the held arrow (arrow1's Haved / Haved2, on the string
# while Failnaught draws) is put on his right hand, which holds it
ARTICLE_FX = {'master_bow': ('havel', {}), 'master_axe': ('haver', {'top': 'axe'}),
              'master_arrow1': ('haver', {'top': 'arrow'})}
# (the whip sword's own effect scripts (Extend: master_wire_flash / _wind) are on the whip article since v6:
# tools/master_whip.py; v5 merged them onto his Sword1, collapsed)
# article script -> the Ultimate body animations (their slots get it merged into their effect script)
ARTICLE_FX_SCRIPTS = {
    ('master_bow', 'SpecialNStart'): ('d00specialnstart', 'd00specialairnstart'),
    ('master_bow', 'SpecialN'): ('d00specialn', 'd00specialairn'),
    ('master_arrow1', 'Haved'): ('d00specialnstart', 'd00specialairnstart'),
    ('master_arrow1', 'Haved2'): ('d00specialnstart', 'd00specialairnstart'),
    ('master_axe', 'AttackLw4'): ('c04attacklw4',), ('master_axe', 'AttackAirLw'): ('c05attackairlw',),
    ('master_axe', 'LandingAirLw'): ('c05landingairlw',), ('master_axe', 'SpecialLw'): ('d03speciallw',),
    ('master_axe', 'SpecialAirLw'): ('d03specialairlw',), ('master_axe', 'SpecialLwHit'): ('d03speciallwhit',),
    ('master_axe', 'SpecialAirLwHit'): ('d03specialairlwhit',),
    ('master_axe', 'SpecialLwLanding1'): ('d03speciallwlanding1',)}


def slot_scripts(fighter):
    """{Ultimate body animation: [the Smash 4 script names of the slots that play it]} from his main.pac's names"""
    import omo
    import ultimate_fighter as UF
    prof = UF.PROFILES['szerosuit']
    out = {}
    for n, _d in omo.pac_read(os.path.join(fighter, 'motion/body/main.pac')):
        key = n[len('FitSZerosuitBodyMain'):-4].lower()
        ult = prof.get('motion_overrides', {}).get(key) or prof['motions'].get(key) or key
        out.setdefault(ult, []).append(key[3:])
    return out


def merge_timed(a, b):
    """merge_flat for a body script with short condition blocks (Float / Int_Var_Compare, True(skip), ..., Else(skip),
    ...: the facing tests the translator writes) holding no FRAME / WAIT: each block is kept whole at its frame, b's
    (flat) commands go in by frame. None if a block waits or b branches"""
    import ultimate_acmd as U
    cmds = [c for c in a if c.ident != acmd.END]
    pos, w = [], 0
    for c in cmds:
        pos.append(w)
        w += 1 + len(c.params)
    at = {p: i for i, p in enumerate(pos)}
    items, t, i = [], 0, 0
    while i < len(cmds):
        c = cmds[i]
        if c.name == 'FRAME':
            t = max(t, int(c.params[0]))
            i += 1
            continue
        if c.name == 'WAIT':
            t += int(c.params[0])
            i += 1
            continue
        if c.name in ('Float_Var_Compare', 'Int_Var_Compare') and i + 1 < len(cmds) and cmds[i + 1].name == 'True':
            j = at.get(pos[i + 1] + int(cmds[i + 1].params[0]))
            if j is None:
                return None
            if cmds[j - 1].name == 'Else':
                j = at.get(pos[j - 1] + int(cmds[j - 1].params[0]), len(cmds) if pos[j - 1] + int(
                    cmds[j - 1].params[0]) == w else None)
                if j is None:
                    return None
            block = cmds[i:j]
            if any(x.name in ('FRAME', 'WAIT', 'JUMP', 'Loop_Rest', 'Goto') for x in block):
                return None
            items.append((t, block))
            i = j
            continue
        if c.name in ('True', 'Else', 'Loop_Rest', 'JUMP', 'Goto', 'IS_RANDOM', 'Float_Var_Compare', 'Int_Var_Compare'):
            return None
        items.append((t, [c]))
        i += 1
    tb = U.merge_flat(b, end())
    if tb is None:
        return None
    t = 0
    for c in tb:
        if c.ident == acmd.END:
            break
        if c.name == 'FRAME':
            t = int(c.params[0])
        else:
            items.append((t, [c]))
    out, t = [], 0
    for when, blk in sorted(items, key=lambda x: x[0]):
        if when > t:
            out.append(U.cmd('FRAME', when))
            t = when
        out += blk
    return out + end()


def article_effects(a, fighter, effect, joints, game=None):
    """Ultimate's held-weapon article effect scripts (Failnaught's glow / drawn arrow / shot flash, Aymr's blade flares)
    merged into the body effect scripts of the moves (Byleth v3 played none: e.g. Failnaught's charge showed only the
    foot dust). Their bones: the article root on the fighter bone it is linked to (ARTICLE_FX), the others by the
    article's bind (EffectTranslator's parents / locals: an offset and turn along the blade)"""
    import numpy as np
    import ssbh_data_py as s
    import ultimate_acmd as U
    import ultimate_tints
    ids = {}
    for p in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(MDIR, 'master_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(p)).items() if not k.startswith('_')})
    parents, locals_ = {}, {}
    rename = {}
    for art, (link, extra) in ARTICLE_FX.items():
        mdir = os.path.join(a.ult, 'model', art.split('_', 1)[1], 'c00')
        if not os.path.exists(mdir + '/model.nusktb'):
            mdir = None
        names = {}
        if mdir:
            sk = s.skel_data.read_skel(mdir + '/model.nusktb')
            for b in sk.bones:
                new = 'art_%s_%s' % (art[7:], b.name.lower())
                names[b.name.lower()] = new
                if extra is None:                       # collapsed onto the link bone
                    parents[new] = link
                elif b.parent_index is None:
                    parents[new] = link                      # the root: replaced by the link
                else:
                    parents[new] = 'art_%s_%s' % (art[7:], sk.bones[b.parent_index].name.lower())
                    locals_[new] = np.array(b.transform, float)
        for old, new in (extra or {}).items():          # the article's own top (not the fighter's)
            names[old] = 'art_%s_%s' % (art[7:], new)
            parents.setdefault(names[old], link)
        rename[art] = names
    tr = U.EffectTranslator(joints, ids, parents, locals_, ultimate_tints.tints('master')
                            if ultimate_tints.fighter_tint('master') else {}, ultimate_tints.script_colours(
                                os.path.join(a.dump, 'master')))
    slots = slot_scripts(fighter)
    log, done = [], []
    for (art, src), anims in ARTICLE_FX_SCRIPTS.items():
        path = os.path.join(a.dump, art, src + '.txt')
        if not os.path.exists(path):
            continue
        body = U.functions(open(path).read()).get('effect_' + src.lower())
        if body is None:
            continue
        for old, new in rename[art].items():
            body = re.sub(r'Hash40::new\("%s"\)(?=, *-?[\d.])' % re.escape(old), 'Hash40::new("%s")' % new, body)
        U.EFFECT_CONDS = (U.LR_LEFT,)
        tr.last, tr.last_name = False, None
        tr.turned_off = set(re.findall(r'EFFECT_OFF_KIND\(agent, Hash40::new\("([^"]+)"', body))
        cmds = tr.script(body)
        U.EFFECT_CONDS = ()
        off = 0
        if anims and isinstance(anims[0], tuple):
            anims, off = anims
        if off:                                         # the article's script starts at the body's frame off
            t, shifted = 0, [U.cmd('FRAME', off)]
            for c in cmds:
                if c.name == 'FRAME':
                    shifted.append(U.cmd('FRAME', int(c.params[0]) + off))
                else:
                    shifted.append(c)
            cmds = shifted
        for anim in anims:
            for name in slots.get(anim, ()):
                k = acmd.crc(name)
                if game is not None and not [c for sc in (effect.scripts.get(k, []), game.scripts.get(k, []))
                                             for c in sc if c.ident != acmd.END]:
                    continue                            # a slot he doesn't play (ZSS's D02SpecialAirHi: emptied)
                m = U.merge_flat(effect.scripts.get(k, end()), cmds) or merge_timed(effect.scripts.get(k, end()), cmds)
                if m is None:
                    log.append('article effects: %s %s -> %s: a branching script, left out' % (art, src, name))
                    continue
                effect.scripts[k] = m
                done.append('%s/%s -> %s' % (art[7:], src, name))
    log.append('article effects merged (%d): %s' % (len(done), ', '.join(done)))
    if tr.missing:
        log.append('article effects without an id: %s' % ', '.join(sorted(tr.missing)))
    return log


def Translator_script(U, joints, body):
    tr = U.Translator(joints)
    out = tr.script(body)
    return out


# ---------------------------------------------------------------- the arrows and the whip (his weapon kinds)
# Failnaught's arrows: copies of ZSS's Paralyzer shot (paralyzer_bullet: native, straight, removed on a hit), his
# articles 6 (arrow1, Ultimate's arrow1 Fly: 12 damage) and 7 (arrow2, the max arrow: Ultimate's arrow2 Search, 29);
# every one of the shot's eight motions plays it (the native shot picks its motion by charge / custom move). The whip:
# a copy of hers (article 2, the tether's ledge reach) carrying the Sword of the Creator's whip since v6 (tools/master_whip.py)
SHOT_MOTIONS = ('7044fcbe', '18de2129', '6fd911bf', 'f1bd841c', 'e4e481dd', '1e08f097', '690fc001', 'f76b55a2')
ARROWS = {'arrow1': ('master_arrow1', 'Fly', 'game_fly', 'effect_fly'), 'arrow2': ('master_arrow2', 'Search', 'game_search',
                                                                                    'effect_search')}
# the shot's params in his vl (its block, read by both copies' getters: speed / life, uncharged and charged): Ultimate's
# param_arrow1 speed_x 9 / life 17; the max arrow's distance 300 (param_arrow2) at speed 10 (mine: its speed isn't in
# vl.prc) over 30 frames
SHOT_PARAMS = {'paralyzer_bullet:0x02000000': 9.0, 'paralyzer_bullet:0x02000001': 10.0,
               'paralyzer_bullet:0x12000002': 17, 'paralyzer_bullet:0x12000003': 30}


def weapons(a, fighter, effect_ids):
    import ultimate_acmd as U
    log = []
    mt = b''.join(bytes.fromhex(x) for x in SHOT_MOTIONS)
    for art, (folder, src, gname, ename) in ARROWS.items():
        fns = U.functions(open(os.path.join(a.dump, folder, src + '.txt')).read())
        game = U.Translator({}).script(fns[gname])
        etr = U.EffectTranslator({}, effect_ids, {})
        eff = etr.script(fns[ename]) if ename in fns else end()
        # its effects end with its flight (the shot's life, SHOT_PARAMS; a hit removes it earlier): port_check E10
        life = 17 if art == 'arrow1' else 30
        made = sorted({c.params[0] for c in eff if c.name.startswith(('Graphic_Effect', 'External_Graphic',
                                                                      'EFFECT_FOLLOW'))})
        if made:
            eff = U.merge_flat(eff, [U.cmd('FRAME', life)] + [U.cmd('Terminate_Graphic_Effect', m, 0, 0) for m in made]
                               + end()) or eff
        snd = end()
        wdir = os.path.join(fighter, 'script/animcmd/weapon', art)
        os.makedirs(wdir, exist_ok=True)
        for fn, sc in (('game', game), ('effect', eff), ('sound', snd), ('expression', end())):
            acmd.ACMDFile({int(x, 16): [acmd.Command(c.ident, list(c.params)) for c in sc] for x in SHOT_MOTIONS}).save(
                os.path.join(wdir, fn + '.bin'))
        open(os.path.join(wdir, 'motion.mtable'), 'wb').write(mt)
        log.append('%s: %s' % (art, '; '.join(str(c) for c in game)[:160]))
        # its MSC: the shot's (its statuses: the flight, the motion its scripts run off, its life). Byleth v1-v3
        # shipped none: the arrows were made with no status and never flew, hit or drew (user: "Neutral special also
        # never fires its projectile"). The max arrow takes the shot's charged branch always (its flag 0x21000000 is
        # ZSS's charge, which his Failnaught doesn't set): motion 4, life 0x12000003
        mdir = os.path.join(fighter, 'script/msc', art)
        os.makedirs(mdir, exist_ok=True)
        src = os.path.join(a.base, 'script/msc/paralyzer_bullet/paralyzer_bullet.mscsb')
        if art == 'arrow1':
            shutil.copy(src, os.path.join(mdir, art + '.mscsb'))
        else:
            log.append(arrow2_msc(src, os.path.join(mdir, art + '.mscsb')))
    # the whip: the Sword of the Creator's (tools/master_whip.py: Ultimate's sword article on her whip's skeleton, its
    # motions under her whip's motion names, its scripts), her MSC (the tether's native-side logic)
    import master_whip
    master_whip.build_model(a.ult, a.base, os.path.join(fighter, 'model/body/c00'), os.path.join(fighter, 'model/whip/c00'),
                            log.append)
    table = master_whip.build_motions(a.ult, a.base, os.path.join(fighter, 'motion/whip/main.pac'), log.append)
    master_whip.build_scripts(a.dump, a.ult, a.base, fighter, effect_ids, table, log.append)
    os.makedirs(os.path.join(fighter, 'script/msc/whip'), exist_ok=True)
    shutil.copy(os.path.join(a.base, 'script/msc/whip/whip.mscsb'), os.path.join(fighter, 'script/msc/whip/whip.mscsb'))
    # Ultimate's up-special hitboxes on `throw`, which his status code keeps on the sword's tip: the converted body
    # motions get a ThrowN track there (male body / female body2)
    for folder, cdir in (('body', 'c00'), ('body2', 'c01')):
        pac = os.path.join(fighter, 'motion', folder, 'main.pac')
        if os.path.exists(pac):
            master_whip.bake_throw(a.ult, pac, os.path.join(fighter, 'model/body', cdir, 'model.vbn'), log.append)
    return log


def arrow2_msc(src, out):
    """the max arrow's MSC: ZSS's shot decompiled (tools/mscdec), its Shoot status's charge test made always true,
    recompiled (msclang)"""
    with tempfile.TemporaryDirectory() as t:
        c = os.path.join(t, 'arrow2.c')
        run(os.path.join(HERE, 'mscdec/mscdec.py'), '-x', os.path.join(HERE, 'mscinfo.xml'), src, '-o', c)
        text = open(c).read()
        old = 'if (WorkModule(0x10, 0x21000000))'
        assert text.count(old) == 1, 'arrow2: the shot\'s charge test not found once'
        text = text.replace(old, 'if (0x1) // Byleth: the max arrow is always the charged shot (was ' + old[4:-1] + ')')
        open(c, 'w').write(text)
        compile_msc(c, out)
    return 'arrow2: the shot\'s MSC, always charged (%d bytes)' % os.path.getsize(out)


# ---------------------------------------------------------------- the vl file
def vl_fix(a, pkg):
    import fighter_param_vl as V
    import ultimate_acmd as U
    path = os.path.join(pkg, 'param/fighter/fighter_param_vl_master.bin')
    vf = V.load(path, 'szerosuit')
    ml = U.read_motion_list(os.path.join(a.ult, 'motion/body/c00/motion_list.bin'))
    n = len([1 for p, _t, *_ in vf.leaves() if re.match(r'm0\[\d+\]\.0$', p)])
    log, changed = [], []

    def tok(i, k):
        (_p, t), = V.find(vf, 'm0[%d].%d' % (i, k), '0', {})
        return t
    for i in range(FIRST_OWN, n):
        if i in FINAL:
            continue
        want = [0, 0, 0, 0]
        if i in PLAYED:
            src = PLAYED[i]
            ent = [e for e in ml if U.hash40('game_' + src.lower()) in (e['game'],) + tuple(e['scripts'])]
            if ent and len(ent[0]['extra']) >= 3:
                xs, xe, cancel = ent[0]['extra'][:3]
                want = [cancel, xs, xe, 0]
        for k, v in zip((2, 3, 4, 5), want):
            t = tok(i, k)
            if t.value != v:
                changed.append('0x%X.%d %d->%d' % (i, k, t.value, v))
                t.set(v)
    for key, v in SHOT_PARAMS.items():
        for _p, t in V.find(vf, key, 'all', {}):
            t.set(v)
    open(path, 'wb').write(vf.build())
    log.append('vl motion bytes (0x211 - 0x25C): %d changed: %s' % (len(changed), ', '.join(changed)))
    log.append('vl: the shot\'s params (his arrows): %s' % ', '.join('%s=%s' % kv for kv in SHOT_PARAMS.items()))
    return log


# his sword trails: Ultimate's tex_master_sword1 (colour) / sword2 (mask) for trail shader 3 (tools/ultimate_trails.py
# --shader 3, as Sephiroth's), trail ids 270 / 271 (tools/trail_table_cave.py NEW_TRAILS; master_effects.json)
TRAILS = ['tex_master_sword1.nutexb,tex_master_sword2.nutexb=TexMasterSwordTrace']


def trails(fighter):
    import port_sources
    tdir = port_sources.load().find('ult_effects', 'master/trail')
    assert tdir, 'port_sources ult_effects: no master/trail'
    return run(os.path.join(HERE, 'ultimate_trails.py'), '--shader', '3', tdir,
               os.path.join(fighter, 'effect/master/trail'), *TRAILS).strip().splitlines()


def cmd_build(a):
    fighter = os.path.join(a.pkg, 'fighter', 'master')
    ids = {}
    for p in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(MDIR, 'master_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(p)).items() if not k.startswith('_')})
    for line in body_fix(a, fighter):
        print(line)
    for line in weapons(a, fighter, ids):
        print(line)
    for line in vl_fix(a, a.pkg):
        print(line)
    for line in trails(fighter):
        print('trails: ' + line)
    out = compile_msc(os.path.join(MDIR, 'master.c'), os.path.join(fighter, 'script/msc/master.mscsb'))
    print('master.mscsb: %d bytes %s' % (os.path.getsize(os.path.join(fighter, 'script/msc/master.mscsb')),
                                         out.strip().splitlines()[-1] if out.strip() else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('vis')
    v.add_argument('dump')
    v.add_argument('ult')
    v.add_argument('out')
    b = sub.add_parser('build')
    for x in ('dump', 'ult', 'body', 'model', 'base', 'pkg'):
        b.add_argument(x)
    b.add_argument('--sound')
    a = ap.parse_args()
    if a.cmd == 'vis':
        cmd_vis(a)
    else:
        cmd_build(a)


if __name__ == '__main__':
    main()
