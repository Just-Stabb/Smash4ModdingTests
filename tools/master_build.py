#!/usr/bin/env python3
"""Byleth's moves (fighters/master/README.md): his held weapons' visibility, his specials' scripts and slots, his MSC,
his arrows (the copied Paralyzer shot, weapon kind 0x19E) and the vl motion bytes of every slot he plays.

  python3 tools/master_build.py vis DUMP ULT OUT.json
  python3 tools/master_build.py build DUMP ULT BODY MODEL BASE PKG [--sound DIR]
  python3 tools/master_build.py hi BODY_SCRIPT_DIR      v12: the up special's hit / overtake scripts on an installed script/animcmd/body

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
    # (v7) the caught fighter's pull: param_special_hi rewind_speed 4.1, param_sword fighter_offset 8 (his hand short
    # of the caught point); the catch's reach: object_dist_max 55 + param_sword reach_length_max 70 (as |dx| + |dy|);
    # the pull's frame cap (mine: 70 / 4.1 = 17, rounded up)
    MASTER_HI_REWIND='4.1f', MASTER_HI_FIND_DIST='125.0f', MASTER_HI_PULL_MAX='0x14',
    # (v12) the overtake (Ultimate's f_7208a1f1d0: his root constrained to the caught fighter's `throw` joint; the
    # motions' hips: special_air_hi_hit_pose (-0.3 fwd, 8.0 up), special_air_hi_overtake frame 0 (-8.1, -6.2)): the reel
    # ends 7.8 behind / 14.2 below that point, the overtake puts him on it; the throw joint's height when the target's
    # waist can't be read (mine: about a body's middle); the throw's frame (ATK_HIT_ABS at 11); the wall jump's
    # REQ_EFFECT (its effect script's frame 6: sys_cling)
    MASTER_HI_OVT_DX='7.8f', MASTER_HI_OVT_DY='14.2f', MASTER_HI_OVT_Y='10.0f', MASTER_HI_OVT_HIT='11.0f',
    MASTER_HI_WJ_FX='6.0f',
    # (v8) the catch: the grab box's TargetStatus (HI_CAPTURE_STATUS, 0xBD the Falcon Dive capture) as the status variable
    # reads it; Ultimate's TARGET_HI_DAMAGE (the overtake's THROW_MEWTWO): the caught fighter at param_special_hi
    # overtake_attack_damage (50) % or more (APPROXIMATED: the flag's test is in the ExeFS, not read)
    MASTER_HI_CAPTURE='189.0f', MASTER_HI_HI_DAMAGE='50.0f', MASTER_HI_CATCH_START='20.0f', MASTER_HI_CATCH_END='26.0f',
    # (v9) Ultimate's SpecialHi main loop (lua2cpp f_7208a2f5e0): TURN_CHECK (the scripts' frame 8) once, the stick back
    # past the common param status_start_turn_stick_x (0.3); the B-reverse window (mine: the move's first 4 frames);
    # the stage line test from his hand (Ultimate's map collision point: hip + map_coll_offset (0, 8, 8): here his hand
    # on Ultimate's timeline, master_whip.py tips) to the tip, frames 17 (EXTEND) - 26 (BACK at 27); a wall: its normal
    # within wall_angle_min / max (+-69 degrees: |ny| <= sin 69); the stops: hit_stop_frame_wall 12 /
    # hit_stop_frame_fighter 19; the catching hit's damage (SpecialAirHi's ATTACK 0 from frame 20: 3 %)
    MASTER_HI_TURN_CHECK='8.0f', MASTER_HI_TURN_STICK='0.3f', MASTER_HI_BREV_END='4.0f', MASTER_HI_LINE_START='17.0f',
    MASTER_HI_LINE_END='26.0f', MASTER_HI_LINE_X='5.5f', MASTER_HI_LINE_Y='20.5f', MASTER_HI_WALL_NY='0.934f',
    MASTER_HI_STOP_WALL='0xc', MASTER_HI_STOP_FIGHTER='0x13', MASTER_HI_CATCH_DAMAGE='3.0f',
    # Aymr: param_special_lw super_armor_damage_max; SpecialLw's START / END_SUPER_ARMOR (34 / 64), INHERIT_LANDING_1's
    # end (51), INHERIT_LANDING_2 (65 - 117)
    MASTER_LW_ARMOR='30.0f', MASTER_LW_ARMOR_START='34.0f', MASTER_LW_ARMOR_END='64.0f', MASTER_LW_INHERIT1_END='51.0f',
    MASTER_LW_INHERIT2_START='65.0f', MASTER_LW_INHERIT2_END='117.0f',
    # (v7) SpecialLw's FORBID_LANDING (60), the axe's PIERCE_GROUND (64 - 65), TURN_CHECK (12 - 42)
    MASTER_LW_FORBID_START='60.0f', MASTER_LW_PIERCE='64.0f', MASTER_LW_TURN_START='12.0f', MASTER_LW_TURN_END='42.0f',
    # (v9) Aymr's critical: param_special_lw critical_slow_rate 4, critical_frame 40; the KO test's stand-in (mine: the
    # hit's hitstun 56 = knockback 140, about a KO from mid-stage on a diagonal)
    MASTER_LW_CRIT_SLOW='0x4', MASTER_LW_CRIT_FRAME='0x28', MASTER_LW_CRIT_HITSTUN='56.0f',
    # (v10) the catch without a capture (master_hi_catch's fallback: Ultimate's hit on the tip catches what it touches,
    # the status holds it): the tip within MASTER_HI_SOFT_REACH of the fighter's body (its feet + 4 to + 18; mine: the
    # catching hit's 5.5 + a body's half width) on two frames running (the grab box gets the first); the wall jump:
    # param_special_hi wall_jump_stop_frame 13 (he clings, then jumps); the tether box: the normal box (vl entry 0) on
    # AIR_LASSO_FLAG_CHECK's frames before SpecialAirHi's select_cliff_hangdata (15), the AIR_LASSO box (entry 2) from
    # there to the flag's end (17)
    MASTER_HI_SOFT_REACH='10.5f', MASTER_HI_WJ_STOP='13.0f', MASTER_HI_LASSO_BOX='15.0f',
    # (v10) Aymr: SpecialAirLw's KineticModule::add_speed (0, 1) at 53 (the translator drops it: no hop, he landed
    # inside 53 - 60 and lost the hit) and the end of its hitbox (67): a landing from the hop to there keeps the air
    # motion and its hit (Ultimate: the hop, then FORBID_LANDING 60 - 65)
    MASTER_LW_HOP='53.0f', MASTER_LW_HOP_Y='1.0f', MASTER_LW_HIT_END='67.0f',
    # (v9) the diag build's log lines (master.c master_diag): 0 normally; compile_msc(..., diag=True) for the test build
    MASTER_DIAG='0')


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def compile_msc(src, out_path, diag=False):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = open(src).read()
    consts = dict(CONSTS, MASTER_DIAG='1' if diag else '0')
    for k in sorted(consts, key=len, reverse=True):
        text = text.replace(k, consts[k])
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
          0x241: 'SpecialLw', 0x245: 'SpecialAirLw', 0x255: 'SpecialLwLanding1', 0x259: 'SpecialLwLanding2',
          0x242: 'SpecialLwHit', 0x243: 'SpecialLwTurn', 0x247: 'SpecialAirLwTurn'}
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
    assert HI_LEDGE_CHECK[1] == 17, 'the whip goes out at 17, with the flag off'
    # the whip hidden until it goes out (status 0 plays no motion of ours: her aircatch hides it so too); his body sword
    # shows until then (SWORD_VIS)
    # v9: the ledge box check (the common AirCatch's: func_99 with flag 0x2100000D, the tether box, vl group 7 entry 2)
    # on Ultimate's AIR_LASSO_FLAG_CHECK frames (12 - 17), not her zair's 0 - 5 (gone before his sword is out: only
    # the whip tip's own latch caught a ledge, user: "very specific")
    whip = [U.cmd('GENERATE_ARTICLE', 2), U.cmd('Article_Visibility', 2, 0),
            U.cmd('FRAME', HI_LEDGE_CHECK[0]), U.cmd('ON_FLAG', 0x2100000D),
            U.cmd('FRAME', HI_LEDGE_CHECK[1]), U.cmd('OFF_FLAG', 0x2100000D),
            U.cmd('Article_Visibility', 2, 1), U.cmd('Set_Remote_Article_Action', 2, 1),
            U.cmd('FRAME', 27), U.cmd('Set_Remote_Article_Action2', 2, 3),
            U.cmd('FRAME', 35), U.cmd('Remove_Article', 2)] + end()
    if any(c.name == 'GENERATE_ARTICLE' for c in g[ac]):
        # this step's output already (the step run again on its build): the merges below are done
        hi_fix(files, log)
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
    # v8: a real throw (the caught fighter, master.c master_hi_throw: the thrown link event and the throw work ints)
    ov = acmd.crc('specialairhiovertake')
    g[ov] = [c for c in g[ov] if c.name not in ('Throw_Specifier', 'Throw_Applier', 'Throw_Specifier2')]
    # v8: the sword tip's catch (Ultimate's ENABLE_CATCH from 20 to the clear at 25): a grab box over the hit's (ID 0)
    for name in ('aircatch', 'specialhi'):
        no_release(g[acmd.crc(name)])
        m = U.merge_flat(g[acmd.crc(name)], tip_catch(U, g[acmd.crc(name)]))
        assert m is not None, name
        g[acmd.crc(name)] = m
    for name, ult in VEC_SCRIPTS:                        # v10: 368 -> a plain angle (port_check S19)
        log.append('%s: the vec-target hits\' angles %s' % (name, pull_angles(g[acmd.crc(name)], a.dump, ult)))
    # Aymr: the axe's hitbox (Ultimate's master_axe SpecialLw / SpecialAirLw: on the axe's haver, which follows his)
    # (v7) and SpecialLwHit's: the axe stuck in the floor, its four ground shock hits at frame 2 (8 %, Ultimate's
    # MOVE_ATTACK slides them out natively: here they stay on the axe)
    for src, name in (('SpecialLw', 'speciallwstart'), ('SpecialAirLw', 'specialairlwstart'), ('SpecialLwHit', 'speciallwhit')):
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
    g[acmd.crc('specialairhihit')] = hi_hit_script()       # v9: the sword stays on what it met during the stop
    files['effect'].scripts[acmd.crc('specialairhihit')] = hi_hit_effect(U, files['effect'])     # v11: the catch's
    for line in smash_hold_fx(a, files['effect'], joints):
        log.append(line)
    g[ov] = merge_tail(U, g[ov], overtake_soft(U, overtake_throw(U, a.dump, joints)))
    hi_fix(files, log)
    for fn, f in files.items():
        f.save(os.path.join(d, fn + '.bin'))
    log.append('aircatch: the whip at 0 / 17 / 27 / 35, the tip\'s catch 20 - 25; specialhi: the catch; overtake: the '
               'throw (THROW / CATCH / THROW_MEWTWO by VAR_12 / 13); Aymr: the axe\'s hitbox merged')
    return log


# v8 the up special's catch (Ultimate: ENABLE_CATCH at 20, AttackModule::clear_all at 25: the hit on `throw` catches)
HI_CATCH_START, HI_CATCH_END = 20, 25
HI_LEDGE_CHECK = (12, 17)        # v9: SpecialAirHi's AIR_LASSO_FLAG_CHECK (on 12, off 17)
HI_HIT_MODE_VAR = 0x0F00030F     # v9: VAR_15, master.c's SpecialAirHiHit mode (1 a wall, 2 a fighter, 0 stopped)
HI_STOP = {1: 12, 2: 19}         # v9: param_special_hi hit_stop_frame_wall / _fighter: the sword back after the stop


def if_var(var, method, value, body):
    """Float_Var_Compare(var, method, value) True { body } (methods 0 ==, 1 !=, 2 <=, 3 >=, 4 <, 5 >)"""
    import ultimate_acmd as U
    return [U.cmd('Float_Var_Compare', var, method, float(value)), U.cmd('True', 2 + U.words(body))] + body


def hi_hit_script():
    """v9 SpecialAirHiHit's game script: the sword goes back (her whip's back status, 3) when master.c's stop ends:
    at 12 for a wall, 19 for a fighter (Ultimate's hit_stop_frame_wall / _fighter: the sword stays on what it met),
    at once when the tip was stopped by a floor / ceiling (VAR_15, set before the motion starts)"""
    import ultimate_acmd as U
    back = lambda: [U.cmd('Set_Remote_Article_Action2', 2, 3)]        # noqa: E731
    out = if_var(HI_HIT_MODE_VAR, 0, 0, back())
    for mode, fr in sorted(HI_STOP.items(), key=lambda kv: kv[1]):
        out += [U.cmd('FRAME', fr)] + if_var(HI_HIT_MODE_VAR, 0, mode, back())
    # v11: a catch without a capture (VAR_11 1 - 3): Ultimate's catching hit (SpecialAirHi's ATTACK 0 from 20: 3 %,
    # sting, cut-up sound) lands on the held fighter at frame 1, its spark, sound and hitlag, no knockback (it stays
    # held); the capsule covers the tip's path over the catch frames (20 - 26: (15, 45) - (23, 65) from him); v12 the
    # blade's too, from his hand (5.5, 20.5): master.c catches a fighter the blade reaches (point-blank)
    hit = U.cmd('Extended_Special_Hitbox', 0)
    f = dict(ID=0, Part=0, Bone=0, Damage=HI_CATCH_HIT, Angle=361, KBG=0, FKB=0, BKB=0, Size=8.0, X=0.0, Y=HI_CATCH_Y0,
             Z=HI_CATCH_Z0, Effect=2, Trip=0.0, Hitlag=1.0, SDI=0.0, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=0, SFXType=3,
             **{'Ground/Air': 3, 'Direct/Indirect': 1}, Type=10, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0,
             Shieldable=0, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=0,
             NoGrabRelease=1, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, X2=0.0, Y2=68.0, Z2=24.0)
    hit.params = [f[n] for n in hit.info['syntax']]
    soft = [U.cmd('FRAME', 1)] + if_var(HI_SOFT_VAR, 5, 0, [hit]) + [U.cmd('FRAME', 2), U.cmd('Remove_All_Hitboxes')]
    k = next(i for i, c in enumerate(out) if c.name == 'FRAME')       # after the frame-0 branch (absolute FRAMEs)
    return out[:k] + soft + out[k:] + end()


HI_CATCH_HIT = 3.0
HI_CATCH_Y0, HI_CATCH_Z0 = 20.0, 6.0     # v12: the catching hit's capsule from his hand (v11: 40, 12, the tip's path only)
HI_CATCH_FX = ((0x347006E, 'master_wire_catch'), (0x3470073, 'master_wire_wind2'))   # master.c master_hi_hit_main
HI_HIT_SE = 0x1B00FB             # v12: se_master_special_h04 (Ultimate's SpecialHiHit status code plays it: every hit)
OVT_SOFT_PART = 1                # v12: the overtake's hitbox Part (the catching hit's is 0, in the same status)
OVT_SOFT_HB = dict(X=0.0, Y=-3.0, Z=0.0, Size=9.0)   # v12: on the caught fighter (his root on its throw point)


def hi_hit_effect(U, effect):
    """SpecialAirHiHit's effect script: none of its own (v12). Ultimate's catch effects are the sword article's
    (SpecialHiHit: master_wire_catch / master_wire_wind2 on the tip, sword35): master.c plays them at the point the tip
    holds (master_hi_fx_at). v11 put them here as Graphic_Effect, the game's FOOT_EFFECT, which it plays only while the
    fighter's foot effects are on (on the ground; EffectModule vt +0x32C, the ACMD handler 0x02BE1444): he is in the
    air in 0x15B, so they never showed (user's v11 test). port_check E14 foot-effect"""
    return end()


def hi_hit_sound(U):
    """v12 SpecialAirHiHit's sound script: Ultimate's SpecialHiHit status plays se_master_special_h04 on every hit (a
    fighter or a wall: VAR_15 1 / 2; not the floor / ceiling stop, 0), its sound script se_master_special_h03 at 2"""
    return if_var(HI_HIT_MODE_VAR, 1, 0, [U.cmd('Sound_Effect', HI_HIT_SE)]) + [
        U.cmd('FRAME', 2), U.cmd('Sound_Effect', 0x1B00FA)] + end()


def overtake_part(script):
    """v12: the overtake's soft-catch hitboxes (VAR_11 1 - 3) on Part OVT_SOFT_PART, on the caught fighter: the catching
    hit (SpecialAirHiHit's frame 1, Part 0) is in the same status (0x15B), and a Part's hit record lasts the status
    (docs/acmd-extra-commands.md "Hit_Log_Clear"): v11's overtake hitbox (Part 0) could never hit the fighter the
    catching hit had (user's v11 test: "the follow-up never hits"). port_check S22 status-hit-log. Returns the count"""
    n, frame = 0, 0.0
    for c in script:
        if c.name == 'FRAME':
            frame = float(c.params[0])
        elif c.name == 'Special_Hitbox' and frame >= 11.0:
            syn = c.info['syntax']
            c.params[syn.index('Part')] = OVT_SOFT_PART
            for k, v in OVT_SOFT_HB.items():
                c.params[syn.index(k)] = v
            n += 1
    return n


def hi_fix(files, log):
    """v12: the up special's hit / overtake scripts as v12 has them (also on a build the specials step ran on before)"""
    import ultimate_acmd as U
    files['effect'].scripts[acmd.crc('specialairhihit')] = hi_hit_effect(U, files['effect'])
    files['sound'].scripts[acmd.crc('specialairhihit')] = hi_hit_sound(U)
    files['game'].scripts[acmd.crc('specialairhihit')] = hi_hit_script()
    n = overtake_part(files['game'].scripts[acmd.crc('specialairhiovertake')])
    assert n == 3, 'the overtake: %d soft hitboxes' % n
    log.append('v12 specialairhihit: no FOOT_EFFECT (the catch effects from MSC), se_master_special_h04; the overtake\'s '
               'soft hitboxes on Part %d, on the caught fighter' % OVT_SOFT_PART)


HI_CAPTURE_STATUS = 0xBD         # the Falcon Dive capture (docs/acmd-params/throws-grabs-other.md TargetStatus 189)
HI_TARGET_VARS = ('FIGHTER_MASTER_STATUS_SPECIAL_HI_FLAG_TARGET_AIR', 0x0F00030C,      # VAR_12, VAR_13: master.c
                  'FIGHTER_MASTER_STATUS_SPECIAL_HI_FLAG_TARGET_HI_DAMAGE', 0x0F00030D)  # master_hi_catch sets them


def tip_catch(U, script):
    """grab boxes where the up special's hitbox ID 0 is, from HI_CATCH_START until the clear (HI_CATCH_END): Extended_Grab_
    Collision (its capsule, bone, size), TargetStatus HI_CAPTURE_STATUS, both situations"""
    frame, out, seen = 0.0, [], False
    for c in script:
        if c.name == 'FRAME':
            frame = float(c.params[0])
        elif c.name == 'WAIT':
            frame += float(c.params[0])
        elif c.name in ('Special_Hitbox', 'Extended_Special_Hitbox') and c.params[0] == 0 and frame >= HI_CATCH_START:
            syn = c.info['syntax']
            v = {k: c.params[syn.index(k)] for k in syn}
            x2 = [v.get(k, v[k[0]]) for k in ('X2', 'Y2', 'Z2')]
            out += [U.cmd('FRAME', frame), U.cmd('Extended_Grab_Collision', 0, v['Bone'], v['Size'], v['X'], v['Y'], v['Z'],
                                                  HI_CAPTURE_STATUS, 3, *x2)]
            seen = True
    assert seen, 'no hitbox ID 0 from frame %d' % HI_CATCH_START
    return out + [U.cmd('FRAME', HI_CATCH_END), U.cmd('Remove_All_Grab_Collisions')] + end()


def merge_tail(U, flat, script):
    """a flat script merged with one whose branches all come at its last frame command (the overtake's throw at frame
    11): the flat part up to that frame merged with the script's head, then the branches, then the flat part's later
    frames (their FRAME commands are absolute: the branches wait for nothing)"""
    k = next(i for i, c in enumerate(script) if c.name in ('Float_Var_Compare', 'Int_Var_Compare'))
    last = max([float(c.params[0]) for c in script[:k] if c.name == 'FRAME'] or [0.0])
    m = U.merge_flat(flat, script[:k] + end())
    assert m is not None, 'merge_tail: a branching script'
    m = [c for c in m if c.ident != acmd.END]
    fr, cut = 0.0, len(m)
    for i, c in enumerate(m):
        if c.name == 'FRAME':
            fr = float(c.params[0])
        elif c.name == 'WAIT':
            raise AssertionError('merge_tail: a WAIT in the merged script')
        if fr > last:
            cut = i
            break
    head = m[:cut]
    if max([float(c.params[0]) for c in head if c.name == 'FRAME'] or [0.0]) < last:
        head.append(U.cmd('FRAME', last))       # merge_flat drops a trailing FRAME: the branches wait for it
    return head + [c for c in script[k:] if c.ident != acmd.END] + m[cut:] + end()


def no_release(script):
    """the catch frames' hitboxes (Ultimate's 3 % on the tip, the hit that catches) with NoGrabRelease: hitting the
    fighter the tip's grab box holds doesn't let it go (port_check S5's rule for throws).
    v9: and they don't touch fighters at all (HitBits bit 0 off: items / stage gimmicks still): v8's grab box shared
    frame 20 with them, the hit took the fighter (its knockback, 3 %; the catcher and it in hitlag) and the grab never
    caught (user's v8 clips: DK hit at 120 -> 123 %, launched, never held). The catch is the grab box alone; master.c
    adds the 3 % to the caught fighter (master_hi_catch). port_check S14 grab-vs-hit"""
    frame = 0.0
    for c in script:
        if c.name == 'FRAME':
            frame = float(c.params[0])
        elif c.name == 'WAIT':
            frame += float(c.params[0])
        elif c.name in ('Special_Hitbox', 'Extended_Special_Hitbox') and frame >= HI_CATCH_START:
            syn = c.info['syntax']
            c.params[syn.index('NoGrabRelease')] = 1
            c.params[syn.index('HitBits')] = int(c.params[syn.index('HitBits')]) & ~1


# v10: Ultimate's angle-368 pulls (set_vec_target_pos: the hit fighter carried to a point): the translator writes 368
# as 366, which in Smash 4 takes the hitbox's own per-frame motion; on a body hit (bone 0, `top`: the ground up special
# at 16) that launched the fighter far out of the sword's way (user's v9 clip 2: DK 0 -> 1 %, gone off the top in 3
# frames; log attempt 1: the fighter in Damage 0x46 from frame 15, never in reach). The MSC pull (master_vt_specialhi /
# _attackhi4) carries them; the hit takes a plain angle toward the point (the ground up special's 16: 74; the up smash's
# 13 / 14: 110 / 67; the tip's 0.01 % pulls 90). port_check S19 vec-pull-angle
PULL_ANGLE_TIP = 90
VEC_SCRIPTS = (('specialhi', 'SpecialHi'), ('aircatch', 'SpecialAirHi'), ('attackhi4', 'AttackHi4'))


def pull_angles(script, dump, ult):
    """the hits Ultimate writes at 368 with set_vec_target_pos (tools/vec_target.py scan): a body hit (`top`) points at
    its target (from the hitbox's centre, forward / up), a hit on the sword's tip (`throw`) straight up (90); the MSC
    pull carries the fighter the rest of the way. Returns [(frame, id, angle)]"""
    import math
    import vec_target as VT
    t = VT.scan(os.path.join(dump, 'master')).get(ult, {}).get('targets', [])
    want = {}
    for e in t:
        hb = e['hitbox']
        if hb['bone'] == 'top':
            want[(e['frame'], e['id'])] = int(round(math.degrees(math.atan2(e['y'] - hb['y'], e['x'] - hb['z'])))) % 360
        else:
            want[(e['frame'], e['id'])] = PULL_ANGLE_TIP
    frame, done = 0.0, []
    for c in script:
        if c.name == 'FRAME':
            frame = float(c.params[0])
        elif c.name == 'WAIT':
            frame += float(c.params[0])
        elif c.name in ('Special_Hitbox', 'Extended_Special_Hitbox'):
            syn = c.info['syntax']
            k = (frame, c.params[0])
            if k in want and int(c.params[syn.index('Angle')]) == 366:
                c.params[syn.index('Angle')] = want[k]
                done.append((frame, c.params[0], want[k]))
    return done


HI_SOFT_VAR = 0x0F00030B          # v10: VAR_11, master.c's catch without a capture: 0 none, 1 THROW, 2 CATCH, 3 MEWTWO


def overtake_soft(U, script):
    """v10: the overtake's throw when the catch had no capture (master_hi_catch's fallback, VAR_11 1 - 3): Ultimate's
    ATTACK_ABS numbers (the Throw_Specifiers this script sets) as a hitbox on the held fighter at the throw's frame (11:
    ATK_HIT_ABS); the Throw_Applier branches only when VAR_11 is 0 (a real capture)"""
    k = next(i for i, c in enumerate(script) if c.name in ('Float_Var_Compare', 'Int_Var_Compare'))
    head, branch = script[:k], [c for c in script[k:] if c.ident != acmd.END]
    spec = {}
    for c in script:
        if c.name == 'Throw_Specifier':
            syn = c.info['syntax']
            v = {n: c.params[syn.index(n)] for n in ('Kind', 'Damage', 'Angle', 'KBG', 'BKB')}
            spec.setdefault(('mew' if spec.get(0) and v['Kind'] == 0 and int(v['KBG']) != int(spec[0]['KBG']) else
                             int(v['Kind'])), v)
    out = head + if_var(HI_SOFT_VAR, 0, 0, branch)
    for val, key in ((1, 0), (2, 1), (3, 'mew')):
        v = spec[key]
        f = dict(ID=0, Part=OVT_SOFT_PART, Bone=0, Damage=float(v['Damage']), Angle=int(v['Angle']), KBG=int(v['KBG']),
                 FKB=0, BKB=int(v['BKB']), **OVT_SOFT_HB, Effect=0, Trip=0.0, Hitlag=1.0, SDI=1.0, Clang=1,
                 Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=3, **{'Ground/Air': 3, 'Direct/Indirect': 1}, Type=10,
                 HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0,
                 Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=0, NoGrabRelease=0, TeamDamage=0,
                 DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0)
        hb = U.cmd('Special_Hitbox', 0)
        hb.params = [f[n] for n in hb.info['syntax']]
        out += if_var(HI_SOFT_VAR, 0, val, [hb])
    return out + [U.cmd('FRAME', 12), U.cmd('Remove_All_Hitboxes')] + end()


def overtake_throw(U, dump, joints):
    """Ultimate's SpecialAirHiOvertake throw: ATTACK_ABS THROW (the ground target's) and CATCH (the air one's) set at
    frame 0, THROW_MEWTWO (an air target at high damage) set where it is thrown (Smash 4 has two absolute slots; the
    translator's frame-0 THROW_MEWTWO took the THROW slot for every case), ATK_HIT_ABS at frame 11 by Ultimate's flags
    (VAR_12 / VAR_13, set by master.c)"""
    text = open(os.path.join(dump, 'master', 'SpecialAirHiOvertake.txt')).read()
    abs_ = {k: re.search(r'macros::ATTACK_ABS\(agent, \*FIGHTER_ATTACK_ABSOLUTE_KIND_%s, [^;]*;' % k, text).group(0)
            for k in ('THROW', 'CATCH', 'THROW_MEWTWO')}
    hit = lambda k: ('macros::ATK_HIT_ABS(agent, *FIGHTER_ATTACK_ABSOLUTE_KIND_%s, Hash40::new("throw"), 0, 0, 0);' % k)  # noqa
    mew = abs_['THROW_MEWTWO'].replace('KIND_THROW_MEWTWO, 2,', 'KIND_THROW, 0,')
    src = ('if macros::is_excute(agent) { %s %s } frame(agent.lua_state_agent, 11.0); '
           'if WorkModule::is_flag(agent.module_accessor, *%s) { '
           'if WorkModule::is_flag(agent.module_accessor, *%s) { if macros::is_excute(agent) { %s %s } } '
           'else { if macros::is_excute(agent) { %s } } } else { if macros::is_excute(agent) { %s } }'
           % (abs_['THROW'], abs_['CATCH'].replace('KIND_CATCH, 1,', 'KIND_CATCH, 0,'), HI_TARGET_VARS[0], HI_TARGET_VARS[2],
              mew, hit('THROW'), hit('CATCH'), hit('THROW')))
    old = dict(U.DYNAMIC_CONDS)
    U.DYNAMIC_CONDS[HI_TARGET_VARS[0]] = ('float', HI_TARGET_VARS[1], 0, 1.0)
    U.DYNAMIC_CONDS[HI_TARGET_VARS[2]] = ('float', HI_TARGET_VARS[3], 0, 1.0)
    try:
        fn = U.functions('unsafe extern "C" fn game_x(agent: &mut L2CAgentBase) {\n%s\n}\n'
                         % src.replace('{ ', '{\n').replace('; ', ';\n').replace(' }', '\n}'))['game_x']
        out = U.Translator(joints).script(fn)
    finally:
        U.DYNAMIC_CONDS.clear()
        U.DYNAMIC_CONDS.update(old)
    names = [c.name for c in out]
    assert names.count('Throw_Applier') == 3 and names.count('Float_Var_Compare') == 2, names
    return out


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


# v9 (user: "please fix Byleth's orb glows when charging Smash attacks"): the smash holds' effect scripts were still
# Zero Suit Samus's (the translator has no Charge -> Hold names): her flash on the hand (RHaveN, (0, 1.5, 2)) in all
# three. Ultimate's AttackS4Charge / AttackHi4Charge / AttackLw4Charge: the dust every 10 frames and sys_smash_flash_s
# on haver (the held weapon's grip = RHaveN) at the weapon's charge point: Areadbhar's head (0, 24, 0), the sword
# (0, 6, 1), Aymr's head (0, 16, 1), random 3; port_check E13 smash-hold
HOLD_FX = (('AttackS4Charge', 'attacks4hold'), ('AttackHi4Charge', 'attackhi4hold'), ('AttackLw4Charge', 'attacklw4hold'))


def smash_hold_fx(a, effect, joints):
    import ultimate_acmd as U
    ids = {}
    for p in (os.path.join(ROOT, 'reference/ultimate_sys_effects.json'), os.path.join(MDIR, 'master_effects.json')):
        ids.update({k: int(v, 0) for k, v in json.load(open(p)).items() if not k.startswith('_')})
    out = []
    for src, dst in HOLD_FX:
        fns = U.functions(open(os.path.join(a.dump, 'master', src + '.txt')).read())
        etr = U.EffectTranslator(joints, ids, {})
        sc = etr.script(fns['effect_' + src.lower()])
        assert any(c.name.startswith('Graphic_Effect') for c in sc), '%s: no effect translated (%s)' % (src, etr.missing)
        effect.scripts[acmd.crc(dst)] = sc
        out.append('%s -> %s: %s' % (src, dst, '; '.join(str(c) for c in sc if c.name.startswith('Graphic'))[:200]))
    return out


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
# param_arrow1 speed_x 9 / life 17. The max arrow (v7): Ultimate's arrow2 doesn't fly, its Search status calls the
# ExeFS's WeaponSpecializer_MasterArrow1::set_search (main.bin 0x03443100): param_arrow2 distance (300) x scale along
# its facing, cut at the first ground (a GroundModule line test), and ONE attack line from the bow to that end on the
# shot's frame: it crosses the stage at once. v1-v6 flew it at 10 a frame for 30 frames (mine; user v6: "hits
# opponents far too slow"). v7 flew it 300 in 4 frames (75 a frame): user v7 "doesn't spawn its line and doesn't have
# a hitbox" - its speed is the shot's NATIVE speed (ZSS's specializer moves the shot, the charged speed only for her
# charge flag, which arrow2 never has: 9 a frame for 4 frames = 36 units, the 1.2-unit hitbox and the beams buried in
# the shot flash), and a hitbox that jumps 75 a frame (60x its size) can't be relied on to meet anyone between frames.
# v8: the arrow stands where it is made (the charged speed 0; the uncharged one is arrow1's, shared block) and its
# game script is ONE line: Ultimate's three ATTACKs (29 %, 361, 56 / 53, size 1.2, lateral -2 / 0 / 2) as capsules
# from the arrow along its facing to ARROW2_DIST (param_arrow2 distance 300), on its first two frames (the native shot
# is removed on its first hit: everyone in the line that frame is hit). Not cut at the ground (no line test reachable
# from MSC / ACMD: APPROXIMATED, fighters/master/README.md "Status v8")
ARROW2_DIST = 300.0         # param_arrow2 distance
ARROW2_SEG = 10.0           # param_arrow2 0x1ef274cc23 (10): the beam pieces' spacing (the beam set is 9.5 long x 1.055)
ARROW2_FX_SCALE = 1.055     # param_arrow2 effect_max_scale
ARROW2_FX_OFFSET = 8.0      # param_arrow2 effect_max_offset_x: the first piece's start ahead of the arrow
ARROW2_LIFE = 10            # the arrow (its beam, its bullet) lasts as the beam set does (~10 frames, fx_render)
ARROW2_HIT_FRAMES = 2
SHOT_PARAMS = {'paralyzer_bullet:0x02000000': 9.0, 'paralyzer_bullet:0x02000001': 0.0,
               'paralyzer_bullet:0x12000002': 17, 'paralyzer_bullet:0x12000003': ARROW2_LIFE}
# the max arrow's own effects (Ultimate requests them from its status code / set_arrow_max_effect, not its ACMD, so
# v1-v6 had none of them): the beam (master_bow_arrow2, Ultimate stretches it from the bow to the end: here its pieces
# every ARROW2_SEG along the line, x effect_max_scale, from effect_max_offset_x), the bullet (the arrow head) and the
# end flash (set_arrow_max_end_effect) at the line's end. Non-following: they outlive the arrow (a hit removes it)
ARROW2_PIECES = int((ARROW2_DIST - ARROW2_FX_OFFSET) // ARROW2_SEG) + 1
ARROW2_FX = (''.join('macros::EFFECT(agent, Hash40::new("master_bow_arrow2"), Hash40::new("top"), 0, 0, %g, 0, 0, 0, %g, '
                     '0, 0, 0, 0, 0, 0, true);' % (ARROW2_FX_OFFSET + ARROW2_SEG * k, ARROW2_FX_SCALE)
                     for k in range(ARROW2_PIECES))
             + 'macros::EFFECT(agent, Hash40::new("master_bow_arrow2_bullet"), Hash40::new("top"), 0, 0, %g, 0, 0, 0, 1, '
               '0, 0, 0, 0, 0, 0, true);' % ARROW2_DIST
             + 'macros::EFFECT(agent, Hash40::new("master_bow_arrow2_end"), Hash40::new("top"), 0, 0, %g, 0, 0, 0, 1, '
               '0, 0, 0, 0, 0, 0, true);' % ARROW2_DIST)


# v9: Ultimate's set_search cuts the max arrow's line at the first ground / wall (a GroundModule line test from the
# arrow along distance 300): here Line_Test (tools/line_test_cave.py, exe_v46v_line) from the arrow along its facing,
# the distance in the arrow's VAR_0; its hitbox capsules and beam stop there, the head and end flash sit there (to
# ARROW2_CUT: the buckets; nothing met = the whole 300). port_check S15 line-cut
ARROW2_CUT = 10.0
ARROW2_CUT_VAR = 0x0F000300


def arrow2_test():
    """Line_Test(Space 0, (0, 0) -> (ARROW2_DIST, 0), Floors 1 (passable platforms left out), Distance -> VAR_0)"""
    import ultimate_acmd as U
    return [U.cmd('Line_Test', 0, 0.0, 0.0, ARROW2_DIST, 0.0, 1, ARROW2_CUT_VAR, 0, 0, 0)]


def arrow2_buckets(make):
    """make(L) for the line cut at L: one block per ARROW2_CUT step, the distance in (L - step, L]; the last one has no
    top (nothing met: the whole length, maybe a hair over it)"""
    out, n = [], int(round(ARROW2_DIST / ARROW2_CUT))
    for k in range(1, n + 1):
        L = ARROW2_CUT * k
        body = make(L)
        if k < n:
            body = if_var(ARROW2_CUT_VAR, 2, L, body)
        out += if_var(ARROW2_CUT_VAR, 5, L - ARROW2_CUT, body)
    return out


def arrow2_line(game):
    """the max arrow's game script: its ATTACKs (Ultimate's, translated) as capsules from the arrow along its facing
    (each at its own lateral offset) to the first stage line within ARROW2_DIST (v9: Line_Test), cleared after
    ARROW2_HIT_FRAMES"""
    import ultimate_acmd as U
    hits = []
    for c in game:
        if c.name == 'Extended_Special_Hitbox':
            syn = c.info['syntax']
            p = list(c.params)
            for k, v in (('Y', 0.0), ('Z', 0.0), ('X2', p[syn.index('X')]), ('Y2', 0.0), ('Z2', ARROW2_DIST)):
                p[syn.index(k)] = v
            hits.append(acmd.Command(c.ident, p))
        elif c.name == 'Special_Hitbox':
            raise AssertionError('arrow2: a plain hitbox in its game script (expected Ultimate\'s capsules)')
        elif c.ident == acmd.END:
            break
        else:
            raise AssertionError('arrow2: %s in its game script (expected its frame-0 capsules only)' % c.name)

    def cut(L):
        out = []
        for h in hits:
            p = list(h.params)
            p[h.info['syntax'].index('Z2')] = L
            out.append(acmd.Command(h.ident, p))
        return out
    return arrow2_test() + arrow2_buckets(cut) + [U.cmd('FRAME', ARROW2_HIT_FRAMES), U.cmd('Remove_All_Hitboxes')] + end()


def arrow2_fx(etr):
    """v9: the beam's pieces up to the cut (a piece where the line goes on past its middle), the head and end flash at
    the cut (ARROW2_FX's effects, cut by the arrow's Line_Test)"""
    one = lambda src: [c for c in etr.script('if macros::is_excute(agent) { %s }' % src) if c.ident != acmd.END]  # noqa: E731
    piece = ('macros::EFFECT(agent, Hash40::new("master_bow_arrow2"), Hash40::new("top"), 0, 0, %g, 0, 0, 0, %g, 0, 0, 0, '
             '0, 0, 0, true);')
    tip = ('macros::EFFECT(agent, Hash40::new("master_bow_arrow2_%s"), Hash40::new("top"), 0, 0, %g, 0, 0, 0, 1, 0, 0, 0, '
           '0, 0, 0, true);')
    out = arrow2_test()
    for k in range(ARROW2_PIECES):
        z = ARROW2_FX_OFFSET + ARROW2_SEG * k
        out += if_var(ARROW2_CUT_VAR, 3, z + ARROW2_SEG / 2, one(piece % (z, ARROW2_FX_SCALE)))
    return out + arrow2_buckets(lambda L: one(tip % ('bullet', L)) + one(tip % ('end', L)))


def weapons(a, fighter, effect_ids):
    import ultimate_acmd as U
    log = []
    mt = b''.join(bytes.fromhex(x) for x in SHOT_MOTIONS)
    for art, (folder, src, gname, ename) in ARROWS.items():
        fns = U.functions(open(os.path.join(a.dump, folder, src + '.txt')).read())
        game = U.Translator({}).script(fns[gname])
        if art == 'arrow2':
            game = arrow2_line(game)
        etr = U.EffectTranslator({}, effect_ids, {})
        eff = etr.script(fns[ename]) if ename in fns else end()
        # its effects end with its flight (the shot's life, SHOT_PARAMS; a hit removes it earlier): port_check E10
        life = 17 if art == 'arrow1' else ARROW2_LIFE
        made = sorted({c.params[0] for c in eff if c.name.startswith(('Graphic_Effect', 'External_Graphic',
                                                                      'EFFECT_FOLLOW'))
                       and c.params[0] not in (effect_ids.get('master_bow_arrow2'), effect_ids.get('master_bow_arrow2_end'),
                                               effect_ids.get('master_bow_arrow2_bullet'))})
        if made:
            eff = U.merge_flat(eff, [U.cmd('FRAME', life)] + [U.cmd('Terminate_Graphic_Effect', m, 0, 0) for m in made]
                               + end()) or eff
        if art == 'arrow2':
            eff = arrow2_fx(etr) + eff          # v9: frame 0, ahead of Ultimate's own (the beam cut at the wall)
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
    h = sub.add_parser('hi', help='v12: the up special\'s hit / overtake scripts (hi_fix) on DIR\'s game / effect / '
                                  'sound .bin (an installed body script folder)')
    h.add_argument('dir')
    a = ap.parse_args()
    if a.cmd == 'vis':
        cmd_vis(a)
    elif a.cmd == 'hi':
        files = {fn: acmd.ACMDFile.load(os.path.join(a.dir, fn + '.bin')) for fn in ('game', 'effect', 'sound')}
        log = []
        hi_fix(files, log)
        for fn, f in files.items():
            f.save(os.path.join(a.dir, fn + '.bin'))
        print('\n'.join(log))
    else:
        cmd_build(a)


if __name__ == '__main__':
    main()
