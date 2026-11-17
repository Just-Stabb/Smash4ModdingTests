#!/usr/bin/env python3
"""Ultimate ACMD (game scripts, as decompiled to smashline Rust: WuBoytH/SSBU-Dumped-Scripts,
smashline/lua2cpp_<fighter>/<fighter>/<Motion>.txt) -> Smash 4 game.bin scripts
(docs/ultimate-fighter-port.md, "Moves").

  python3 tools/ultimate_acmd.py SCRIPT_DIR GAME_BIN OUT_GAME_BIN MODEL_DIR [--only NAME...] [--list]
      [--others IN_DIR OUT_DIR] [--motion-list MOTION_LIST --mtable IN OUT --vl IN OUT] [--translate JSON]

MODEL_DIR: the fighter's converted model/body/c00 (model.vbn + model.jtb: Ultimate bone names ->
ACMD joint IDs). Every script in TRANSLATE is converted and replaces the base's script of the same
Smash 4 name; the rest of GAME_BIN stays.

What maps to what:
- frame(n) / wait(n) -> FRAME / WAIT; FT_MOTION_RATE(r) -> Set_Frame_Duration(r)
- ATTACK -> Special_Hitbox for a sphere, Extended_Special_Hitbox for a capsule (never with its end at its
  start: in game that hit the whole stage), with the value tables below
  (effect, sound, region, facing, clank, situation, categories; taken from vanilla scripts:
  Cloud / Marth / Ike / Ganondorf / Pikachu); set_weight -> Set_Weight_Hitbox
- AttackModule::clear_all / clear(id) / set_size(id, size) -> Remove_All_Hitboxes / Remove_Hitbox /
  Change_Hitbox_Size
- CATCH -> Grab_Collision / Extended_Grab_Collision (sphere / capsule); grab clear -> Remove_All_Grab_Collisions; the common capture
  cut -> CALL 0x49FA5BDD (as Cloud's catches)
- ATTACK_ABS -> Throw_Specifier; ATK_HIT_ABS -> Throw_Applier (the throw work ints 0x11000005-7)
- HIT_NODE / WHOLE_HIT -> Set_Bone_Intangibility / Body_Collision; REVERSE_LR -> Reverse_Direction
- status flags (FLAGS) -> ON_FLAG / OFF_FLAG of the Smash 4 status variables
- conditions: macros::is_excute is always true; any other condition (One-Winged Angel, a floor hit)
  is taken as false (its else branch runs)
Anything else is left out and counted (--list prints it per script).

--others: the base's effect.bin / sound.bin (IN_DIR) with the translated scripts emptied (the base's
effects and sounds would play on our moves) and expression.bin with an empty script for any
translated motion it lacks (a motion the base doesn't have, e.g. attack12), written to OUT_DIR.

--motion-list (Ultimate's motion/body/c00/motion_list.bin) with --mtable / --vl: per translated
motion, the motion_list entry whose game script is game_<file>: its cancel frame and intangible
frames go into fighter_param_vl group 1 (bytes 2 / 3 / 4: the same three numbers, e.g. Cloud's
DownAttackU 46 / 1 / 26 in both games); a common motion the base has no script for (attack12 /
attack13 for a one-jab base) gets its motion.mtable entry (and vl byte 0 = 1, as non-looping
motions; 0 where Ultimate's motion_list flags it looping, 0x2). Landing motions are left as they are (their lag is fighter_param's). With --base-rpx /
--base-kind, prints the motions whose Ultimate "move" flag (0x4, the root moves the fighter; the
same bit as the low byte of a Smash 4 motion table entry's flags) differs from the base's, and
the slots the base leaves empty, as the "motions" of the kind's extra_kinds.json record
(tools/kind_expand.py).
"""
import argparse
import json
import math
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acmd  # noqa: E402

# Ultimate file -> Smash 4 script name (lower case; default: the file name lower-cased)
TRANSLATE = {
    'Attack11': 'attack11', 'Attack12': 'attack12', 'Attack13': 'attack13', 'AttackDash': 'attackdash',
    'AttackS3': 'attacks3', 'AttackS3Hi': 'attacks3hi', 'AttackS3Lw': 'attacks3lw',
    'AttackHi3': 'attackhi3', 'AttackLw3': 'attacklw3',
    'AttackS4': 'attacks4', 'AttackHi4': 'attackhi4', 'AttackLw4': 'attacklw4',
    'AttackAirN': 'attackairn', 'AttackAirF': 'attackairf', 'AttackAirB': 'attackairb',
    'AttackAirHi': 'attackairhi', 'AttackAirLw': 'attackairlw', 'LandingAirLw': 'landingairlw',
    'Catch': 'catch', 'CatchDash': 'catchdash', 'CatchTurn': 'catchturn', 'CatchAttack': 'catchattack',
    'ThrowF': 'throwf', 'ThrowB': 'throwb', 'ThrowHi': 'throwhi', 'ThrowLw': 'throwlw',
    'CliffAttack': 'cliffattackquick', 'DownAttackU': 'downattacku', 'DownAttackD': 'downattackd',
    'SlipAttack': 'slipattack',
    # the aerials' landings (EMPTY: the base's emptied): Ultimate's own game scripts where it has them (Byleth's neutral
    # air landing hit, 1 % at 30 degrees on frame 2: missing up to v5); no vl bytes for landings (fighter_param's landing
    # frames)
    'LandingAirN': 'landingairn', 'LandingAirF': 'landingairf', 'LandingAirB': 'landingairb',
    'LandingAirHi': 'landingairhi',
    # the dash's run transition (Ultimate's frame: 11 for the four ported so far; the base's was for its
    # own animation, Robin 17 / Zelda 16 / Pit 13 / Bowser 14, so the run cut in mid-stride; Smash 4 has
    # no TurnDash motion, its turn dash plays Dash). Game script only: the base's sound / expression
    # scripts (steps) aren't emptied for them (effects: translate_effects as before), and the dash's
    # motion_list frames aren't vl cancel frames
    'Dash': 'dash',
}
GAME_ONLY = {'dash'}
# common moves whose motion slots the base may lack (ZSS has no rapid jab and no angled forward smash): translated
# only with --slot-moves (ultimate_port.py passes the ones whose animations port.json motions.add gives the
# kind: C00Attack100* / C03AttackS4Hi / Lw, with their slots in extra_kinds.json "motions"); a script in a slot
# with no animation would never play, and the common MSC picks 0x5E / 0x61 only when the motion is there
SLOT_MOVES = {'Attack100Start': 'attack100start', 'Attack100': 'attack100', 'Attack100End': 'attack100end',
              'AttackS4Hi': 'attacks4hi', 'AttackS4Lw': 'attacks4lw'}
# their vl cancel frame (group 1 byte 2) from Ultimate's motion_list, the scripts left as they are
CANCEL_ONLY = ('appealhil', 'appealhir', 'appeallwl', 'appeallwr', 'appealsl', 'appealsr')
# Ultimate transition term -> Smash 4 STRANS id (vanilla dash scripts: STRANS_ON(0x1E00000A) at the run frame)
TERMS = {'FIGHTER_STATUS_TRANSITION_TERM_ID_DASH_TO_RUN': 0x1E00000A}
# --translate: script name -> motion slot for the run's extra translations
SLOTS = {}
# base scripts emptied (they'd run the base's moves on a motion we replaced without a script of ours)
EMPTY = ['attacks4hi', 'attacks4lw', 'landingairn', 'landingairf', 'landingairb', 'landingairhi']
# TRANSLATE names emptied when Ultimate has no game script for them (the base's landing hit stayed on
# Squirtle's down air: port_check S7)
EMPTY_IF_ABSENT = {'landingairlw'}
# a TRANSLATE slot whose Ultimate file is absent but whose motion plays another move's animation (the profile's stand-in:
# ultimate_fighter.py) takes that move's script: one forward tilt on a base with angled ones (Byleth on ZSS: her
# AttackS3Hi / Lw hitboxes stayed on his forward-tilt animation, a base leftover: port_check B1)
FALLBACK = {'attacks3hi': 'AttackS3', 'attacks3lw': 'AttackS3'}

EFFECT = {'collision_attr_normal': 0, 'collision_attr_cutup': 2, 'collision_attr_sting': 2,
          'collision_attr_elec': 3, 'collision_attr_fire': 5, 'collision_attr_purple': 0x13,
          'collision_attr_magic': 0, 'collision_attr_paralyze': 0x14, 'collision_attr_sleep': 9,
          'collision_attr_sleep_ex': 9, 'collision_attr_ice': 4,          # freezing (Lucas's PK Freeze)
          'collision_attr_cutup_metal': 2, 'collision_attr_deathball': 0}
SFX_LEVEL = {'ATTACK_SOUND_LEVEL_S': 0, 'ATTACK_SOUND_LEVEL_M': 1, 'ATTACK_SOUND_LEVEL_L': 2, 'ATTACK_SOUND_LEVEL_LL': 3}
SFX_TYPE = {'COLLISION_SOUND_ATTR_NONE': 0, 'COLLISION_SOUND_ATTR_PUNCH': 1, 'COLLISION_SOUND_ATTR_KICK': 2,
            'COLLISION_SOUND_ATTR_CUTUP': 3, 'COLLISION_SOUND_ATTR_ELEC': 7, 'COLLISION_SOUND_ATTR_FIRE': 8,
            'COLLISION_SOUND_ATTR_MAGIC': 8, 'COLLISION_SOUND_ATTR_HEAVY': 8,
            # (Byleth v16) the attributes v1 - v15 didn't list came out as 0, Smash 4's "Nothing": a silent hit (Aymr,
            # COLLISION_SOUND_ATTR_MASTER_AXE, user: "down special has no hit sound"). Smash 4's types
            # (reference/spreadsheets SFX_Type): 3 slash, 9 splash, 0xB explosion, 0x12 slap, 0x1C ice. A fighter's own
            # attribute plays its own HitSE in Ultimate (se_master_hit_axe, se_master_hit_attack100end: Smash 4 has no
            # per-fighter hit sound type for a new kind), so the nearest common one: Aymr's / the rapid jab's
            # finisher / Hero's critical sword hits a slash, the max arrow's pierce a slash, Squirtle's shell a kick
            'COLLISION_SOUND_ATTR_BOMB': 0xB, 'COLLISION_SOUND_ATTR_WATER': 0x9, 'COLLISION_SOUND_ATTR_FREEZE': 0x1C,
            'COLLISION_SOUND_ATTR_SLAP': 0x12, 'COLLISION_SOUND_ATTR_MASTER_AXE': 3,
            'COLLISION_SOUND_ATTR_MASTER_ATTACK100END': 3, 'COLLISION_SOUND_ATTR_MASTER_ARROW_MAX': 3,
            'COLLISION_SOUND_ATTR_BRAVE_CRITICALHIT': 3, 'COLLISION_SOUND_ATTR_ZENIGAME_SHELLHIT': 2}


def sfx_type(attr):
    """Smash 4's SFX type for Ultimate's COLLISION_SOUND_ATTR_*: never a silent 0 for an attribute that sounds
    (port_check S25 hit-sound): one not listed warns and takes a slash (a fighter's own: most are weapons) or a punch"""
    if attr in SFX_TYPE:
        return SFX_TYPE[attr]
    sys.stderr.write('ultimate_acmd: COLLISION_SOUND_ATTR %s not in SFX_TYPE: a stand-in hit sound\n' % attr)
    return 3 if attr.count('_') > 3 else 1
REGIONS = ['NONE', 'HEAD', 'BODY', 'HIP', 'PUNCH', 'ELBOW', 'KICK', 'KNEE', 'THROW', 'OBJECT', 'SWORD', 'HAMMER',
           'BOMB', 'SPIN', 'BITE', 'MAGIC', 'PSI', 'PALUTENA', 'AURA', 'BAT', 'PARASOL', 'PIKMIN', 'WATER',
           'WHIP', 'TAIL', 'ENERGY']
REGION = {'ATTACK_REGION_' + r: i for i, r in enumerate(REGIONS)}
FACING = {'ATTACK_LR_CHECK_F': 3, 'ATTACK_LR_CHECK_B': 4, 'ATTACK_LR_CHECK_POS': 0, 'ATTACK_LR_CHECK_SPEED': 0,
          'ATTACK_LR_CHECK_LR': 3}
# Ultimate's special angles: 367 is kept (Smash 4's exe has a 367 too: like 366, the victim follows the
# hitbox's own motion, but it also pulls a grounded victim, where 366 pulls only one off the ground:
# docs/native-notes.md "Special angles 365 - 367"). User decision (2026-11-16): use 367 from now on; ports
# converted earlier (Squirtle's Waterfall, Hero's Swoosh, Byleth's nair / uair, Incineroar's Final Smash) keep
# their 366 until they are next rebuilt. 368 (to a set point) has no Smash 4 equivalent: written as 366, with
# the point done in MSC (tools/vec_target.py).
ANGLE = {368: 366}
# Holding multi-hits (Byleth v17: "the rapid jab's hits don't connect properly"; rapid_setoff v1: "can you recreate the
# Ultimate setting for rapid jabs?"): Ultimate's ATTACK_SETOFF_KIND_OFF with the Sakurai angle 361 and a small knockback
# (his rapid jab: 0.4 %, KBG 10, BKB 12). Smash 4's 361 sends a grounded victim whose knockback is under 60 at 0 degrees,
# so every hit slides it away until it leaves the hitboxes' reach. (Ultimate's setoff kind itself is the clank kind,
# read from its ExeFS: SETOFF below; Ultimate also scales that 0-degree slide by 0.8, damage_angle_ground_zero_speed_mul:
# docs/native-notes.md "Hitbox hold".)
# HOLD_MODE 'hold' (the default, exe_v46y_hold and later): Ultimate's own angle, and Hitbox_Hold(ID, HOLD_SETTING) after
# the hitbox (tools/hitbox_hold_cave.py: no knockback travel for a grounded victim the hit doesn't lift).
# HOLD_MODE 'angle' (--hold-angle, port.json "rapid_hold": "angle"; for an executable without the cave): v17's
# workaround, HOLD_ANGLE (Smash 4's own rapid jabs hold with a near-vertical angle: Fox 60 - 85, Captain Falcon 75 - 90,
# Sheik 50 - 70, Mewtwo 70 - 89, Robin 80), APPROXIMATED (an airborne victim goes up a little). port_check S28 / X8
HOLD_MODE = 'hold'
HOLD_SETTING = 1
HOLD_ANGLE = 80
HOLD_MAX_KB = 30
# (Byleth v18: "the rapid jab still doesn't work ... how often the hitbox refreshes": one hit per 19-frame loop in the
# user's clip, Ultimate's 6) every holding hit also (1) starts with Hit_Log_Clear of its Part, so each wave's hits
# have a new hit record whatever the slot held before (Ultimate's clear_all + ATTACK makes a new attack each wave), and
# (2) carries Ultimate's hitlag as fixed frames for both sides (Extra hitbox HitstopFrames / SelfHitstopFrames =
# ult_hitlag: floor((damage x 0.65 + 6) x hitlag multiplier), 2 for the rapid jab's 0.4 % x 0.4), so the victim is never
# still in its hitstop when the next wave (3 frames on, in the attacker's time) arrives: a hit on a fighter in hitstop
# is lost (Sephiroth test 112), and the attacker's own hitstop was 0 in the clip (the loop kept its 19 frames).
# port_check S30 rapid-cadence
HOLD_WAVE_CLEAR = True


def ult_hitlag(dmg, mul):
    """Ultimate's hitlag frames for a hit: floor((damage x 0.65 + 6) x the hitbox's multiplier), at least 1"""
    import math
    return max(1, int(math.floor((float(dmg) * 0.65 + 6.0) * float(mul))))


def holding(angle, kbg, fkb, bkb, setoff, dmg):
    """an Ultimate hitbox that holds its victim (setoff off, 361, a small knockback, damage)"""
    return (setoff == 'ATTACK_SETOFF_KIND_OFF' and int(angle) == 361 and float(dmg) > 0 and int(fkb) == 0
            and int(kbg) <= HOLD_MAX_KB and int(bkb) <= HOLD_MAX_KB)


def hold_angle(angle, kbg, fkb, bkb, setoff, dmg):
    """the Smash 4 angle of an Ultimate hitbox (ANGLE; HOLD_ANGLE for a holding multi-hit when HOLD_MODE is 'angle')"""
    if HOLD_MODE == 'angle' and holding(angle, kbg, fkb, bkb, setoff, dmg):
        return HOLD_ANGLE
    return ANGLE.get(int(angle), int(angle))

SETOFF = {'ATTACK_SETOFF_KIND_ON': (1, 1), 'ATTACK_SETOFF_KIND_OFF': (1, 0), 'ATTACK_SETOFF_KIND_THRU': (0, 0)}
# _d: lying fighters too (Byleth's Sword of the Creator); Smash 4's Ground/Air has no such bit
SITUATION = {'COLLISION_SITUATION_MASK_G': 1, 'COLLISION_SITUATION_MASK_A': 2, 'COLLISION_SITUATION_MASK_GA': 3,
             'COLLISION_SITUATION_MASK_G_d': 1, 'COLLISION_SITUATION_MASK_GA_d': 3}
CATEGORY = {'COLLISION_CATEGORY_MASK_ALL': 0x3F, 'COLLISION_CATEGORY_MASK_NO_STAGE_GIMMICK': 0x1F,
            'COLLISION_CATEGORY_MASK_FIGHTER': 0x1, 'COLLISION_CATEGORY_MASK_NO_FIGHTER': 0x3E}
HIT_STATUS = {'HIT_STATUS_NORMAL': 0, 'HIT_STATUS_INVINCIBLE': 1, 'HIT_STATUS_XLU': 2, 'HIT_STATUS_OFF': 2}
# THROW_MEWTWO (Byleth's up-special overtake on an air target with high damage): a throw's
ABS_KIND = {'FIGHTER_ATTACK_ABSOLUTE_KIND_THROW': 0, 'FIGHTER_ATTACK_ABSOLUTE_KIND_CATCH': 1,
            'FIGHTER_ATTACK_ABSOLUTE_KIND_THROW_MEWTWO': 0}
CAPTURE_STATUS = {'FIGHTER_STATUS_KIND_CAPTURE_PULLED': 0x3F}
# Ultimate status flag -> Smash 4 status variable (from vanilla scripts doing the same: Cloud's jabs,
# aerials, catches; Mario's up smash for the smash hold)
FLAGS = {'FIGHTER_STATUS_ATTACK_FLAG_ENABLE_COMBO': 0x2100000D,
         'FIGHTER_STATUS_ATTACK_FLAG_ENABLE_NO_HIT_COMBO': 0x21000013,
         # the jab's restart (hold A: jab 1 again; Link's attack11 / 12 turn it on at 16), the rapid jab's way in
         # (the common jab status 0x25 goes to Attack100 0x26 with it on: Kirby's attack12) and the loop's
         # continue check (the common Attack100 loop reads it each hit: Kirby's attack100, every 4 frames)
         'FIGHTER_STATUS_ATTACK_FLAG_ENABLE_RESTART': 0x2100000E,
         'FIGHTER_STATUS_ATTACK_FLAG_ENABLE_100': 0x21000011,
         'FIGHTER_STATUS_ATTACK_FLAG_100_CONTINUE_CHECK': 0x21000016,
         'FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD': 0x2100001B,
         'FIGHTER_STATUS_ATTACK_AIR_FLAG_ENABLE_LANDING': 0x2100000D,
         'FIGHTER_STATUS_CATCH_FLAG_CATCH_WAIT': 0x2100000D,
         # the common up-special status (Mario's Super Jump Punch: its script turns these on at Ultimate's
         # frames, 4 and 6): the turn with the stick, then the rise by the animation's TransN
         'FIGHTER_STATUS_SUPER_JUMP_PUNCH_FLAG_REVERSE_LR': 0x2100000F,
         'FIGHTER_STATUS_SUPER_JUMP_PUNCH_FLAG_MOVE_TRANS': 0x2100000D}
# notify_event_msc_cmd 0x2127e37c07 (the ledge check) -> Allow/Disallow_Ledgegrab's state (Mario's up special:
# 1 from the rise, 2 at its end)
CLIFF_CHECK = {'GROUND_CLIFF_CHECK_KIND_ALWAYS': 1, 'GROUND_CLIFF_CHECK_KIND_ALWAYS_BOTH_SIDES': 2}
SITUATIONS = {'SITUATION_KIND_GROUND': 0, 'SITUATION_KIND_AIR': 2}
THROW_VARS = (0x11000005, 0x11000006, 0x11000007)
# Ultimate article -> the fighter's Smash 4 article id (--articles NAME=ID,...)
ARTICLES = {}
# Ultimate's helper bones a converted model lacks -> the bone that stands in (virtualcenter: the body's middle)
BONE_ALIAS = {'virtualcenter': 'hip'}
CAPTURE_CUT_CALL = 0x49FA5BDD


def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


# ---------------------------------------------------------------- parsing
def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def value(a):
    a = a.strip()
    if a == 'None':
        return None
    m = re.fullmatch(r'Some\((.*)\)', a)
    if m:
        return value(m.group(1))
    m = re.fullmatch(r'Hash40::new\("(.*)"\)', a)
    if m:
        return m.group(1)
    if a in ('true', 'false'):
        return a == 'true'
    if a.startswith('*'):
        return a[1:].split(' as ')[0].strip()
    a2 = a.split(' as ')[0]
    try:
        return float(a2) if ('.' in a2 or 'e' in a2.lower()) else int(a2, 0)
    except ValueError:
        return a


def functions(text):
    """{name: body} of the `unsafe extern "C" fn name(...) { body }` in a dump file"""
    out = {}
    for m in re.finditer(r'fn (\w+)\(agent: &mut L2CAgentBase\) \{', text):
        i, depth = m.end(), 1
        while depth:
            depth += {'{': 1, '}': -1}.get(text[i], 0)
            i += 1
        out[m.group(1)] = text[m.end():i - 1]
    return out


LOOP_UNROLL = 12           # an endless loop after other statements: its body this many times


def self_jump(cmds, name):
    """a translated endless loop's jump back (JUMP 0, from __loop_jump__) aimed at the script itself"""
    for c in cmds:
        if c.name == 'JUMP' and c.params and c.params[0] == 0:
            c.params[0] = acmd.crc(name)
    return cmds


def statements(body):
    """a flat list of ('call', name, args) / ('if', cond) / ('else',) / ('end',)"""
    out = []
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c.isspace() or c == ';':
            i += 1
            continue
        if c == '}':
            j = i + 1
            while j < n and body[j].isspace():
                j += 1
            if body.startswith('else', j):
                k = body.index('{', j)
                cond = body[j + 4:k].strip()
                if cond.startswith(('if ', 'if(')):
                    out.append(('elseif', cond[2:].strip()))
                else:
                    out.append(('else',))
                i = k + 1
            else:
                out.append(('end',))
                i += 1
            continue
        if body.startswith('if ', i) or body.startswith('if(', i):     # Steve's dump: `if(0x370870(...)){`
            k = i + 2
            depth = 0
            while not (body[k] == '{' and depth == 0):
                depth += {'(': 1, ')': -1}.get(body[k], 0)
                k += 1
            cond = body[i + 2:k].strip()
            # Steve's dump: each material test comes twice, `if(M){ operatorbool()const(is_excute); }
            # else { if(M){ <the hitboxes> } ...`: the first a decompiler stub, taken as false so the
            # real block (in its else) runs
            e, depth = k + 1, 1
            while e < n and depth:
                depth += {'{': 1, '}': -1}.get(body[e], 0)
                e += 1
            inner = body[k + 1:e - 1].strip()
            if inner.startswith('methodlib::L2CValue::operatorbool') and inner.count(';') == 1:
                cond = '__decompiler_stub__'
            out.append(('if', cond))
            i = k + 1
            continue
        if re.match(r'loop\s*\{', body[i:]):
            # an endless loop (the rapid jab's Attack100: every script of it). The whole body -> its statements,
            # then the jump back to the start (Smash 4's form: Kirby's attack100 ends WAIT_LOOP_CLR, JUMP(itself));
            # after other statements (effect_attack100: two effects, then the foot smoke every 8 frames) -> unrolled
            # LOOP_UNROLL times, so what comes before it doesn't play again
            k = body.index('{', i) + 1
            s0, depth = k, 1
            while depth:
                depth += {'{': 1, '}': -1}.get(body[k], 0)
                k += 1
            inner = statements(body[s0:k - 1])
            if not out and not body[k:].strip(' \n\t;'):
                out += [('call', '__loop_begin__', [])] + inner + [('call', '__loop_jump__', [])]
            else:
                out += inner * LOOP_UNROLL
            i = k
            continue
        m = re.match(r'for _ in (\d+)\.\.(\d+) \{', body[i:])
        if m:       # a counted loop (the charge's dust puffs, SpecialNStart): unrolled
            k, depth = i + m.end(), 1
            while depth:
                depth += {'{': 1, '}': -1}.get(body[k], 0)
                k += 1
            out += statements(body[i + m.end():k - 1]) * (int(m.group(2)) - int(m.group(1)))
            i = k
            continue
        # a statement up to its ';' at depth 0
        k, depth = i, 0
        while k < n and not (body[k] == ';' and depth == 0):
            depth += {'(': 1, ')': -1, '{': 1, '}': -1}.get(body[k], 0)
            k += 1
        st = body[i:k].strip()
        i = k + 1
        m = re.match(r'(?:let \w+ = )?([\w:!]+)\s*\((.*)\)$', st, re.S)
        if m:
            out.append(('call', m.group(1), split_args(m.group(2))))
        else:
            out.append(('other', st))
    return out


def fix_misplaced_else(out):
    """the dump's `if C { if is_excute { A } else { B } }`, where the else is C's (Steve's material
    tests: B, the rest of the move, never ran) -> `if C { A } else { B }`"""
    exc = 'macros::is_excute(agent)'

    def close(i):                       # index of the ('else',) / ('end',) closing the block opened at i
        d = 0
        for j in range(i + 1, len(out)):
            k = out[j][0]
            if k == 'if':
                d += 1
            elif k == 'end':
                if d == 0:
                    return j
                d -= 1
            elif k in ('else', 'elseif') and d == 0:
                return j
        return None
    changed = True
    while changed:
        changed = False
        for i in range(len(out) - 1):
            if out[i][0] != 'if' or out[i][1] == exc or out[i + 1] != ('if', exc):
                continue
            e = close(i + 1)
            if e is None or out[e] != ('else',):
                continue
            x = close(e)
            if x is None or out[x] != ('end',) or x + 1 >= len(out) or out[x + 1] != ('end',):
                continue
            out[:] = out[:i + 1] + out[i + 2:e] + [('else',)] + out[e + 1:x] + [('end',)] + out[x + 2:]
            changed = True
            break
    return out


def fix_split_flag_branch(out):
    """the dump's `if is_flag(F) { A } B; operatorbool()const(is_excute); D` (Hero's down smash: its
    critical hit's second part B outside the if, the else marked by the stray operatorbool line) ->
    `if is_flag(F) { A B } else { D }`, D up to the end of the enclosing block"""
    def is_stray(st):
        return st[0] in ('call', 'other') and 'L2CValue::operatorbool' in str(st[1])
    i = 0
    while i < len(out):
        if out[i][0] == 'if' and 'is_flag' in out[i][1]:
            d, end = 0, None
            for j in range(i + 1, len(out)):
                k = out[j][0]
                if k == 'if':
                    d += 1
                elif k == 'end':
                    if d == 0:
                        end = j
                        break
                    d -= 1
                elif k in ('else', 'elseif') and d == 0:
                    break
            mark = close = None
            if end is not None:
                d = 0
                for j in range(end + 1, len(out)):
                    k = out[j][0]
                    if k == 'if':
                        d += 1
                    elif k in ('else', 'elseif') and d == 0:
                        break
                    elif k == 'end':
                        if d == 0:
                            close = j
                            break
                        d -= 1
                    elif is_stray(out[j]) and d == 0 and mark is None:
                        mark = j
            if mark is not None:
                close = len(out) if close is None else close
                out[:] = out[:end] + out[end + 1:mark] + [('else',)] + out[mark + 1:close] + [('end',)] + out[close:]
        i += 1
    return out


def fix_trailing_flag_else(out):
    """the dump's `if F { X } S; if is_excute { W } else { Z }` where the else is F's and S, W its true branch
    (Sephiroth's winged landing: `if WINGED { 2: landing03 } 8: winged_landing02 else { landing03 }`) ->
    `if F { X S if is_excute { W } } else { Z }`. Sound scripts only (SoundTranslator.extra_fixes)"""
    exc = 'macros::is_excute(agent)'

    def close(i):
        d = 0
        for j in range(i + 1, len(out)):
            k = out[j][0]
            if k == 'if':
                d += 1
            elif k == 'end':
                if d == 0:
                    return j
                d -= 1
            elif k in ('else', 'elseif') and d == 0:
                return j
        return None
    i = 0
    while i < len(out):
        if out[i][0] == 'if' and 'is_flag' in out[i][1]:
            e1 = close(i)
            if e1 is not None and out[e1] == ('end',):
                j = e1 + 1
                while j < len(out) and out[j][0] in ('call', 'other'):
                    j += 1
                if j < len(out) and out[j] == ('if', exc):
                    c = close(j)
                    if c is not None and out[c] == ('else',):
                        out[:] = out[:e1] + out[e1 + 1:c] + [('end',), ('else',)] + out[c + 1:]
        i += 1
    return out


def _units(seq):
    """statements -> units: a lone statement, or an `if ... end` block (nested blocks inside)"""
    out, i = [], 0
    while i < len(seq):
        if seq[i][0] == 'if':
            d, j = 0, i
            while j < len(seq):
                d += {'if': 1, 'end': -1}.get(seq[j][0], 0)
                if d == 0:
                    break
                j += 1
            if j >= len(seq):
                return None
            out.append(seq[i:j + 1])
            i = j + 1
        elif seq[i][0] in ('else', 'elseif', 'end'):
            return None
        else:
            out.append(seq[i:i + 1])
            i += 1
    return out


LR_TAG = 'LR_IN_GAME '          # a facing condition fix_lr_split laid out: decided in game (LR_FACING)


def fix_lr_split(out, cond_text):
    """the dump's facing split `if LR { A } R; ... else { B } R'` (the else hung on R's last is_excute
    block; R' the facing-right copy of R, the same shape: Squirtle's smash attacks' water_smash /
    water_smash_r) -> `if LR { A } else { B }`, then R and R' paired unit by unit: a frame (or any
    unit the two share) once, a differing block as `if LR { r } else { r' }`. Waits stay outside the
    condition. Left as it is when the shapes don't match"""
    out = list(out)
    for i, st in enumerate(out):
        if st[0] != 'if' or cond_text not in st[1]:
            continue
        d, j = 0, i
        while j < len(out):
            d += {'if': 1, 'end': -1}.get(out[j][0], 0)
            if d == 0:
                break
            j += 1
        if j >= len(out):
            continue
        if any(x[0] == 'else' for x in out[i:j]):
            # a well-formed `if LR { A } else { B }`: decided in game as it is
            out[i] = ('if', LR_TAG + st[1])
            continue
        # the misplaced else: the first else after j at the depth of a block opened after j
        d, e = 0, None
        for k in range(j + 1, len(out)):
            d += {'if': 1, 'end': -1}.get(out[k][0], 0)
            if d < 0:
                break
            if out[k][0] == 'else' and d == 1:
                e = k
                break
        if e is None:
            continue
        r = out[j + 1:e] + [('end',)]                     # R, its last block closed
        d, x = 1, None
        for k in range(e + 1, len(out)):
            d += {'if': 1, 'end': -1}.get(out[k][0], 0)
            if d == 0:
                x = k
                break
        if x is None:
            continue
        b = out[e + 1:x]                                     # B (the else's own blocks)
        ur = _units(r)
        rest = out[x + 1:]
        ur2 = _units(rest[:len(r)]) if len(rest) >= len(r) else None
        if not ur or not ur2 or len(ur) != len(ur2) or \
                any((len(p) > 1) != (len(q) > 1) for p, q in zip(ur, ur2)):
            continue
        tagged = ('if', LR_TAG + st[1])
        new = out[:i] + [tagged] + out[i + 1:j] + [('else',)] + b + [('end',)]
        for p, q in zip(ur, ur2):
            if p == q or len(p) == 1:
                new += p
            else:
                new += [tagged] + p[1:-1] + [('else',)] + q[1:-1] + [('end',)]
        return fix_lr_split(new + rest[len(r):], cond_text)
    return out


LR_LEFT = 'get_value_float(agent.lua_state_agent, *SO_VAR_FLOAT_LR) < 0.0'
EFFECT_CONDS = ()


# --cond: conditions taken as true, by substring (Steve: his tool's material, e.g.
# 'MATERIAL_KIND_IRON)'; any other condition is false, its else branch runs)
TRUE_CONDS = []


# --dyn-cond: conditions decided in game, not here (substring of the dump's condition -> an int variable):
# the `if` becomes Int_Var_Compare(variable != 0) then True { the if's body } Else { the else's }, both
# kept (Hero's critical hit: FIGHTER_BRAVE_INSTANCE_WORK_ID_FLAG_CRITICAL_HIT, rolled by his MSC). != 0, not
# == 1: Robin's native code counts some of his ints down every frame (0x10000098-0x1000009C, the tomes'
# recharge; 0x02F635F0), so the MSC writes a big value and a tick can't clear it (fix 62)
DYNAMIC_CONDS = {}

# Ultimate's costume tests, decided in game (exe_v46s, tools/costume_group_cave.py): FIGHTER_INSTANCE_WORK_ID_INT_COLOR
# % 2 -> the variable COSTUME_PARITY (0x0F000501: costume & 1), Float_Var_Compare == 1 / == 0 (Byleth: odd costumes
# female, whose timings differ). An older executable reads 0 there: the even (male) branch, as before
COLOR_PARITY = 0x0F000501
DYNAMIC_CONDS.update({'FIGHTER_INSTANCE_WORK_ID_INT_COLOR) % 2 != 0': ('float', COLOR_PARITY, 0, 1.0),
                      'FIGHTER_INSTANCE_WORK_ID_INT_COLOR) % 2 == 0': ('float', COLOR_PARITY, 0, 0.0)})


def dynamic_var(cond):
    """an int variable (tested != 0), ('float', variable, method, value) (Float_Var_Compare) or ('random', N)
    (IS_RANDOM_CHANCE(N): fold_tests' form of Ultimate's IS_RANDOM, Smash 4's IS_RANDOM(Chance=N))"""
    m = re.fullmatch(r'IS_RANDOM_CHANCE\((\d+)\)', cond.strip())
    if m:
        return ('random', int(m.group(1)))
    return next((v for k, v in DYNAMIC_CONDS.items() if k in cond), None)


# the facing in game: position variable 0x0F000003 (1 right, -1 left; docs/position-variables.md),
# method 4 (<): the facing-left branch of Ultimate's `if LR < 0` (its mirrored _r effects in the else)
LR_FACING = ('float', 0x0F000003, 4, 0.0)


def words(cmds):
    return sum(len(c.encode()) // 4 for c in cmds)


def cond_true(cond):
    if cond == 'macros::is_excute(agent)' or cond in EFFECT_CONDS:
        return True
    if cond.startswith('!'):            # before the --cond test: `!is_flag(F)` with F taken as true is false
        return not cond_true(cond[1:].strip())
    if any(c in cond for c in TRUE_CONDS):
        return True
    # the voice region (Byleth's win sounds: `if GET_VOICE_REGION(agent) == *VOICE_US_EN { ... } else { ... }`): the
    # English block, as first_voice_region takes (v1 / v2 took neither: his win sound scripts were empty)
    if re.search(r'GET_VOICE_REGION\(agent\) == \*VOICE_US_EN\b', cond):
        return True
    # the costume's parity (Byleth: even male, odd female, whose animations' timings differ): the male branch, every
    # costume playing the male animations (one motion folder: fighters/master/README.md, female motions to come)
    if re.search(r'FIGHTER_INSTANCE_WORK_ID_INT_COLOR\) % 2 == 0', cond):
        return True
    return False


# ---------------------------------------------------------------- translation
class Translator:
    def __init__(self, joints):
        self.joints = joints            # Ultimate bone name (lower case) -> ACMD joint ID
        self.skipped = {}
        self.frame = 0.0                # the script's frame at the current statement
        self.events = []                # (frame, call, args) of the WorkModule sets (Steve's tool requests)
        self.vec_targets = []           # this script's set_vec_target_pos (tools/vec_target.py: the MSC pull)
        self.raw_hitboxes = {}          # hitbox ID -> its Ultimate ATTACK values (the last made, this script)

    def bone(self, name):
        if name == 'top':
            return 0
        if name not in self.joints and name in BONE_ALIAS and BONE_ALIAS[name] in self.joints:
            name = BONE_ALIAS[name]
        if name not in self.joints:
            raise KeyError('bone %r has no joint ID' % name)
        return self.joints[name]

    def skip(self, what):
        self.skipped[what] = self.skipped.get(what, 0) + 1

    def script(self, body):
        cmds = []
        self.made = []             # the commands made so far (the same objects as in cmds)
        self.frame, self.events = 0.0, []
        self.vec_targets, self.raw_hitboxes = [], {}
        self._wave_cleared = set()  # v18: (frame, Part) already given Hit_Log_Clear before its holding hits
        live = [True]              # a stack of "this block runs"
        taken = [False]
        dyn = []                   # dynamic ifs open: [where its compare goes, where its Else goes or None]
        loop_at = 0                # where an endless loop's body starts (__loop_begin__)
        sts = fix_split_flag_branch(fix_misplaced_else(statements(body)))
        for fix in getattr(self, 'extra_fixes', ()):
            sts = fix(sts)
        if LR_TAG in DYNAMIC_CONDS:
            sts = fix_lr_split(sts, 'SO_VAR_FLOAT_LR) < 0')
        for st in sts:
            kind = st[0]
            if kind == 'if':
                var = dynamic_var(st[1]) if live[-1] else None
                if var is not None:
                    live.append(True)
                    taken.append('dyn')
                    dyn.append([len(cmds), None, var, self.frame])
                    continue
                c = live[-1] and cond_true(st[1])
                live.append(c)
                taken.append(c)
                continue
            if kind == 'elseif':
                assert taken[-1] != 'dyn', 'elseif after a dynamic condition'
                c = live[-2] and not taken[-1] and cond_true(st[1])
                live[-1] = c
                taken[-1] = taken[-1] or c
                continue
            if kind == 'else':
                if taken[-1] == 'dyn':
                    dyn[-1][1] = len(cmds)
                    end_true, self.frame = self.frame, dyn[-1][3]   # the else starts where the if did
                    dyn[-1][3] = end_true
                    continue
                live[-1] = live[-2] and not taken[-1]
                taken[-1] = True
                continue
            if kind == 'end':
                if len(live) > 1:
                    if taken[-1] == 'dyn':
                        at, els, var, other = dyn.pop()
                        if els is None:
                            body_t, body_e = cmds[at:], []
                        else:
                            body_t, body_e = cmds[at:els], cmds[els:]
                            self.frame = max(self.frame, other)
                        if isinstance(var, tuple) and var[0] == 'random':
                            test = cmd('IS_RANDOM', var[1])
                        elif isinstance(var, tuple):
                            test = cmd('Float_Var_Compare', *var[1:])
                        else:
                            test = cmd('Int_Var_Compare', var, 1, 0)        # method 1: !=
                        block = [test, cmd('True', 2 + words(body_t) + (2 if body_e else 0))] + body_t
                        if body_e:
                            block += [cmd('Else', 2 + words(body_e))] + body_e
                        cmds[at:] = block
                    live.pop()
                    taken.pop()
                continue
            if not live[-1]:
                continue
            if kind == 'other':
                self.skip(st[1].split('(')[0][:40])
                continue
            if st[1] == 'wait_loop_clear':          # the loop's frame count back to 0 (Smash 4's WAIT_LOOP_CLR)
                cmds.append(cmd('WAIT_LOOP_CLR'))
                self.frame = 0.0
                continue
            if st[1] == '__loop_begin__':
                loop_at = len(cmds)
                continue
            if st[1] == '__loop_jump__':            # statements(): an endless loop's end, aimed by self_jump()
                # the jump back must come after a wait, or the script spins in one frame (a hang): Ultimate's
                # wait_loop_sync_mot (the run / walk effects: wait for the motion's loop) is Smash 4's Loop_Rest,
                # as the vanilla looping scripts end; a body with no wait at all gets one too
                body_names = {c.name for c in cmds[loop_at:]}
                if getattr(self, 'loop', False) or not body_names & {'WAIT', 'WAIT_LOOP_CLR', 'Loop_Rest'}:
                    cmds.append(cmd('Loop_Rest'))
                cmds.append(cmd('JUMP', 0))
                continue
            got = self.call(st[1], [value(a) for a in st[2]], st[2])
            self.made += got
            cmds += got
        return cmds + [acmd.Command(acmd.END)]

    def add_reaction(self, hid, frames):
        extra = {'Special_Hitbox': 'Extra_Special_Hitbox', 'Extended_Special_Hitbox': 'Extra_Extended_Special_Hitbox'}
        for c in reversed(self.made):
            if c.name in extra and int(c.params[0]) == hid:
                c.ident = acmd.BY_NAME[extra[c.name].lower()]
                c.params = list(c.params) + [-frames, 0.0, 0, 0.0, 0, 0.0]
                return []
            if c.name in extra.values() and int(c.params[0]) == hid:     # v18: already Extra (a holding hit's hitlag)
                c.params[c.info['syntax'].index('HitstunMul')] = -frames
                return []
        self.skip('AttackModule::set_add_reaction_frame (no hitbox %d)' % hid)
        return []

    def call(self, name, a, raw):
        short = name.split('::')[-1]
        if short == 'frame':
            self.frame = max(self.frame, float(a[1]))
            return [cmd('FRAME', int(round(a[1])))]
        if short == 'wait':
            self.frame += float(a[1])
            return [cmd('WAIT', int(round(a[1])))]
        if name in ('WorkModule::set_int', 'WorkModule::on_flag', 'WorkModule::off_flag'):
            self.events.append((self.frame, name, a))
        if short == 'FT_MOTION_RATE':
            return [cmd('Set_Frame_Duration', float(a[1]))]
        if short == 'ATTACK':
            return self.attack(a)
        if short == 'set_vec_target_pos':
            return self.vec_target(a, raw)
        if name == 'AttackModule::set_add_reaction_frame':
            # frames more hitstun for hitbox ID (Magic Burst's 2, so its hits hold): that hitbox (the last
            # made with the ID, in this script so far) as its Extra_ form, HitstunMul = -frames (tools/
            # acmd_ext_cave.py: a negative one adds frames)
            return self.add_reaction(int(a[1]), float(a[2]))
        if name == 'AttackModule::set_catch_only_all':
            # throws: the hitbox hits only the held fighter and keeps the grab. Smash 4's vanilla throw
            # hitboxes on the victim say so with NoGrabRelease 1 (Pikachu's ThrowF); with 0 the hit freed
            # Squirtle's thrown opponent before Throw_Applier (his throws "released" them)
            if a[1]:
                for c in self.made:
                    syn = c.info.get('syntax', [])
                    if 'NoGrabRelease' in syn:
                        c.params[syn.index('NoGrabRelease')] = 1
            return []
        if name == 'AttackModule::clear_all':
            return [cmd('Remove_All_Hitboxes')]
        if name == 'AttackModule::clear':
            return [cmd('Remove_Hitbox', int(a[1]))]
        if name == 'AttackModule::set_size':
            return [cmd('Change_Hitbox_Size', int(a[1]), float(a[2]))]
        if name == 'WorkModule::enable_transition_term':
            t = TERMS.get(a[1])
            if t is None:
                self.skip(name + ' ' + str(a[1]))
                return []
            return [cmd('STRANS_ON', t)]
        if name in ('WorkModule::on_flag', 'WorkModule::off_flag'):
            f = FLAGS.get(a[1])
            if f is None:
                self.skip(name + ' ' + str(a[1]))
                return []
            return [cmd('ON_FLAG' if name.endswith('on_flag') else 'OFF_FLAG', f)]
        if short == 'SA_SET' and str(a[1]) in SITUATIONS:
            return [cmd('SA_SET', SITUATIONS[str(a[1])])]
        if short == 'notify_event_msc_cmd!' and str(a[1]).endswith('0x2127e37c07)') and str(a[2]) in CLIFF_CHECK:
            return [cmd('Allow/Disallow_Ledgegrab', CLIFF_CHECK[str(a[2])])]
        if name == 'ArticleModule::generate_article' and str(a[1]) in ARTICLES:
            return [cmd('GENERATE_ARTICLE', ARTICLES[str(a[1])])]
        if short == 'CATCH':
            return self.catch(a)
        if short == 'grab!' or name == 'GrabModule::clear_all':
            return [cmd('Remove_All_Grab_Collisions')]
        if short == 'game_CaptureCutCommon':
            return [cmd('CALL', CAPTURE_CUT_CALL)]
        if short == 'ATTACK_ABS':
            return self.attack_abs(a)
        if short == 'ATK_HIT_ABS':
            return [cmd('Throw_Applier', ABS_KIND[a[1]], self.bone(a[2]), *THROW_VARS)]
        if short == 'HIT_NODE':
            return [cmd('Set_Bone_Intangibility', self.bone(a[1]), HIT_STATUS.get(a[2], 0))]
        if short == 'WHOLE_HIT':
            return [cmd('Body_Collision', HIT_STATUS.get(a[1], 0))]
        if short == 'REVERSE_LR':
            return [cmd('Reverse_Direction')]
        self.skip(name)
        return []

    def vec_target(self, a, raw):
        """AttackModule::set_vec_target_pos(id, bone, Vector2f{x, y}, frames[, false]) (FighterSpecializer_Edge's
        too): the hitbox's victims are carried to the bone + (x forward, y up) over `frames` (Ultimate's angle 368).
        Smash 4 has no such hitbox field (its 366 / 367 take the victim along with the hitbox's own motion, 366
        only off the ground: 0x02C25CD8); nothing goes in the script: it is recorded (self.vec_targets) for the
        fighter's MSC pull (tools/vec_target.py, the method of Sephiroth's up tilt, test 151), which --vec-targets
        writes out and port_check S10 checks"""
        m = re.search(r'x:\s*([-\d.e]+)\s*,\s*y:\s*([-\d.e]+)', raw[3] if len(raw) > 3 else '')
        if not m:
            self.skip('set_vec_target_pos (unparsed)')
            return []
        hid = int(a[1])
        self.vec_targets.append({'frame': self.frame, 'id': hid, 'bone': a[2], 'x': float(m.group(1)),
                                 'y': float(m.group(2)), 'frames': int(a[4]), 'hitbox': self.raw_hitboxes.get(hid)})
        return []

    def attack(self, a):
        (_ag, hid, part, bone, dmg, angle, kbg, fkb, bkb, size, x, y, z, x2, y2, z2, hitlag, sdi, setoff, lr,
         set_weight, shield_dmg, trip, rehit, reflect, absorb, flinchless, no_hitlag, direct, situation, category,
         partmask, friendly, effect, lvl, attr, region) = a[:37]
        clang, rebound = SETOFF[setoff]
        self.raw_hitboxes[int(hid)] = {'bone': bone, 'angle': int(angle), 'size': float(size), 'x': float(x),
                                       'y': float(y), 'z': float(z), 'x2': x2, 'y2': y2, 'z2': z2,
                                       'situation': SITUATION.get(situation, 3)}
        if not isinstance(shield_dmg, (int, float)) or shield_dmg != shield_dmg:
            shield_dmg = 0              # f32::NAN (Kamikazee's blast): none
        # never below 0 (the user's rule for Ultimate ports, CLAUDE.md): Smash 4 reads ShieldDamage unsigned, so
        # Ultimate's negative ones (Hero's spells, Sephiroth's flares / flash) were a shield break every hit
        shield_dmg = max(shield_dmg, 0)
        common = [int(hid), int(part), self.bone(bone), float(dmg), hold_angle(angle, kbg, fkb, bkb, setoff, dmg), int(kbg), int(fkb), int(bkb), float(size),
                  float(x), float(y), float(z), EFFECT.get(effect, 0), float(trip), float(hitlag), float(sdi), clang,
                  rebound, int(round(shield_dmg)), SFX_LEVEL[lvl], sfx_type(attr), SITUATION[situation],
                  1 if direct else 0, REGION.get(region, 0), CATEGORY.get(category, 0x3F), 0, 0xF, 0, 1,
                  1 if reflect else 0, 1 if absorb else 0, int(rehit), 0, 0, FACING.get(lr, 3), 0, 1 if friendly else 0,
                  1 if no_hitlag else 0, 0, 1 if flinchless else 0]
        if capsule_end(x, y, z, x2, y2, z2) is None:
            # a sphere: Special_Hitbox (Shape 0). As an Extended_Special_Hitbox with its end = its start, every
            # one of Sephiroth's hit the whole stage (test 20: the zero-length capsule's direction is 0 / 0)
            out = [cmd('Special_Hitbox', *common, 0)]
        else:
            out = [cmd('Extended_Special_Hitbox', *common, *capsule_end(x, y, z, x2, y2, z2))]
        if set_weight:
            out.append(cmd('Set_Weight_Hitbox', int(hid), 1))
        if HOLD_MODE == 'hold' and holding(angle, kbg, fkb, bkb, setoff, dmg):
            if HOLD_WAVE_CLEAR:
                hf = ult_hitlag(dmg, hitlag)
                extra = {'Special_Hitbox': 'Extra_Special_Hitbox', 'Extended_Special_Hitbox': 'Extra_Extended_Special_Hitbox'}
                h = out[0]
                h.ident = acmd.BY_NAME[extra[h.name].lower()]
                h.params = list(h.params) + [0.0, 0.0, hf, 0.0, hf, 0.0]
                key = (self.frame, int(part))
                cleared = getattr(self, '_wave_cleared', set())
                if key not in cleared:
                    out.insert(0, cmd('Hit_Log_Clear', int(part)))
                    cleared.add(key)
                    self._wave_cleared = cleared
            out.append(cmd('Hitbox_Hold', int(hid), HOLD_SETTING))
        return out

    def catch(self, a):
        _ag, cid, bone, size, x, y, z, x2, y2, z2, status, situation = a[:12]
        common = [int(cid), self.bone(bone), float(size), float(x), float(y), float(z), CAPTURE_STATUS.get(status, 0x3F),
                  SITUATION[situation]]
        end = capsule_end(x, y, z, x2, y2, z2)
        if end is None:
            return [cmd('Grab_Collision', *common)]
        return [cmd('Extended_Grab_Collision', *common, *end)]

    def attack_abs(self, a):
        _ag, kind, part, dmg, angle, kbg, fkb, bkb, trip, hitlag, lr, _unk, no_reaction, effect, lvl, attr, region = a[:17]
        return [cmd('Throw_Specifier', ABS_KIND[kind], int(part), float(dmg), int(angle), int(kbg), int(fkb), int(bkb),
                    EFFECT.get(effect, 0), float(trip), float(hitlag), 1.0, SFX_LEVEL[lvl], sfx_type(attr),
                    FACING.get(lr, 3), 1, 1 if no_reaction else 0, REGION.get(region, 8))]


def capsule_end(x, y, z, x2, y2, z2):
    """the capsule's other end (Ultimate leaves it None for a sphere), or None for a sphere"""
    end = tuple(float(a if b is None else b) for a, b in ((x, x2), (y, y2), (z, z2)))
    return None if end == (float(x), float(y), float(z)) else end


# ---------------------------------------------------------------- effects
# Ultimate effect macro -> Smash 4 command and the shape of its arguments (matched on the vanilla
# fighters both games share: tools/ultimate_sys_effect_map.py): 'full' = name, bone, x, y, z, rx, ry,
# rz, size, 6 random ranges, terminate; 'follow' = name, bone, x .. rz, size, terminate; '+alpha' /
# '+color' = then an alpha (x 100) / r, g, b (x 255)
EFFECT_MACROS = {
    'EFFECT': ('Graphic_Effect2', 'full'), 'FOOT_EFFECT': ('Graphic_Effect', 'full'),
    'LANDING_EFFECT': ('Graphic_Effect3', 'full'), 'DOWN_EFFECT': ('DOWN_EFFECT', 'full'),
    'EFFECT_ALPHA': ('Graphic_Effect7', 'full+alpha'),
    'EFFECT_FOLLOW': ('External_Graphic', 'follow'), 'EFFECT_FOLLOW_NO_STOP': ('Graphic_Effect4', 'follow'),
    'EFFECT_FLW_POS': ('External_Graphic_Effect2', 'follow'),
    'EFFECT_FLW_POS_NO_STOP': ('External_Graphic_Effect2', 'follow'),
    'EFFECT_FOLLOW_ALPHA': ('Graphic_Effect6', 'follow+alpha'),
    'EFFECT_FOLLOW_COLOR': ('EFFECT_FOLLOW_COLOR', 'follow+color'),
    # Smash 4's own EFFECT_GLOBAL (name, x .. rz, size: no bone); Ultimate's has a trailing bool more (Byleth's Final
    # Smash screens, VisualScene01 / 02)
    'EFFECT_GLOBAL': ('EFFECT_GLOBAL', 'global'),
}

# LAST_EFFECT_SET_* -> the Smash 4 command of the same name, its arguments scaled: Ultimate passes
# rate / alpha / colour as is (app::sv_animcmd -> EffectModule vt+0x338 / +0x348 ...: rate lands in
# the effect record +0x264, a per-set playback speed), Smash 4's alpha is a percent and its colour 0-255
LAST_EFFECT = {'LAST_EFFECT_SET_RATE': 1.0, 'LAST_EFFECT_SET_ALPHA': 100.0, 'LAST_EFFECT_SET_COLOR': 255.0,
               'LAST_PARTICLE_SET_COLOR': 1.0}

# the effect macros Smash 4 has under the same name (its ACMD ids are crc32 of the macro names Ultimate's dumps
# use: EFFECT_FOLLOW_RND = Graphic_Effect5, EFFECT_FOLLOW_FLIP_ALPHA, FOOT_EFFECT_FLIP...), their arguments in the
# same order (acmd_info.json's syntax); the flip types by name (vanilla pairs: Kirby's DownAttackU EF_FLIP_YZ ->
# FlipType 1, EF_FLIP_XY -> 3, on the same effects)
FLIP_TYPES = {'EF_FLIP_NONE': 0, 'EF_FLIP_YZ': 1, 'EF_FLIP_XZ': 2, 'EF_FLIP_XY': 3}
_SYNTAX = None


def same_name_syntax(macro):
    """Smash 4's argument names for the effect command of this macro name, or None"""
    global _SYNTAX
    if _SYNTAX is None:
        import zlib
        info = json.load(open(os.path.join(HERE, 'acmd_info.json')))['commands']
        _SYNTAX = {'%08X' % k: v for k, v in ((int(h, 16), v) for h, v in info.items())}
        _SYNTAX['_crc'] = lambda n: '%08X' % zlib.crc32(n.encode())
    v = _SYNTAX.get(_SYNTAX['_crc'](macro))
    syn = v and v.get('syntax') or []
    # 'Effect': EFFECT_FLW_UNSYNC_VIS / EFFECT_FLW_POS_UNSYNC_VIS name their id field so (Byleth's side special dash)
    return (v['name'], syn) if syn[:1] in (['Graphic'], ['GFXRight'], ['Effect']) and 'Bone' in syn else None


def euler_matrix(rot):
    """effect angles (degrees) -> rotation matrix (column vectors): R = Rz Ry Rx, X turned first.
    Both games: Ultimate's own data needs it (Sephiroth's sword glows, meshes along +Y, lie along the
    blade, +X of swordl2, only so with (0, 180, -90); his up-air arc, a disc about Y, faces the
    camera only so with (2.5, 120, 90)), and the moves both games share keep their angles in this
    convention better than in the other orders (scratch comparison of sys_* effect angles)"""
    import numpy as np
    a, b, c = (math.radians(v) for v in rot)
    rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return rz @ ry @ rx


def euler_xyz(m):
    """euler_matrix's inverse (degrees, rounded to 0.01)"""
    b = math.asin(max(-1.0, min(1.0, -m[2, 0])))
    if abs(m[2, 0]) < 1 - 1e-6:
        a, c = math.atan2(m[2, 1], m[2, 2]), math.atan2(m[1, 0], m[0, 0])
    else:                                                   # gimbal lock: all of it in x
        a, c = math.atan2(-m[1, 2], m[1, 1]), 0.0
    return [round(math.degrees(v), 2) + 0.0 for v in (a, b, c)]


# Ultimate trail blend -> Smash 4 Sword_Glow BlendMode / Shader: Ike's, Marth's and Link's blend 11,
# and trail shader 3, Ultimate's retracting one (tools/trail_shader.py: needs its effect_trail.nsh,
# its executable patch and tools/ultimate_trails.py --shader 3 textures; vanilla trails use 1)
TRAIL_BLEND = (11, 3)


class EffectTranslator(Translator):
    """effect_* functions -> Smash 4 effect scripts. ids: Ultimate effect name -> Smash 4 effect id
    (the common bank's for sys_*; a fighter bank's once converted), and trail texture name -> Smash 4
    trail id (tools/trail_table_cave.py); other names are left out and counted. Bones without a joint
    id use their nearest ancestor that has one (parents: Ultimate's skeleton, lower-case names), the
    offset carried into the ancestor's frame through the bind pose (locals: each bone's local
    transform, row vectors) when it's known."""

    def __init__(self, joints, ids, parents, locals_=None, tints=None, baked=None):
        super().__init__(joints)
        self.ids, self.parents, self.locals = ids, parents, locals_ or {}
        self.missing = {}
        self.last = False
        self.last_name = None
        self.turned_off = set()
        # tools/ultimate_tints.py: the fighter's tint on its attack lines / arcs (baked into the bank: a
        # LAST_EFFECT_SET_COLOR after one replaces it in Ultimate, so it is divided out), and the script colours
        # baked into the bank (the LAST_PARTICLE_SET_COLOR after their effects dropped)
        self.tints, self.baked = tints or {}, baked or {}
        # the script's Ultimate animation (BonePose and its file), for effects placed in the model's frame
        self.pose, self.anim = None, None
        self.unposed = 0

    def bone(self, name):
        return self.bone_at(name, (0.0, 0.0, 0.0))[0]

    def joint_bone(self, name):
        """the bone `name` or its nearest ancestor with a joint id (lower case)"""
        n = name.lower()
        while n not in self.joints and n != 'top' and n in self.parents:
            n = self.parents[n]
        return n

    def bone_chain(self, name):
        """(joint id, bone `name`'s frame in that joint's: 4 x 4, row vectors)"""
        import numpy as np
        n = name.lower()
        m = np.eye(4)
        while n not in self.joints and n != 'top' and n in self.parents:
            if n in self.locals:
                m = m @ self.locals[n]
            n = self.parents[n]
        return super().bone(n), m

    def bone_at(self, name, xyz):
        """(joint id, the point xyz of bone `name` in that joint's frame)"""
        import numpy as np
        jid, m = self.bone_chain(name)
        p = np.array([float(v) for v in xyz] + [1.0]) @ m
        return jid, [float(v) for v in p[:3]]

    def place(self, name, xyz, rot):
        """(joint id, x, y, z, rx, ry, rz) of an effect at xyz / rot (degrees) in bone `name`'s frame,
        in the joint's frame: a bone without a joint id (e.g. Sephiroth's swordl2, 90 degrees off
        his hand's frame) turns the effect too"""
        import numpy as np
        jid, m = self.bone_chain(name)
        p = np.array([float(v) for v in xyz] + [1.0]) @ m
        rot = [float(v) for v in rot]
        if not np.allclose(m[:3, :3], np.eye(3), atol=1e-5):
            rot = euler_xyz(m[:3, :3].T @ euler_matrix(rot))
        return [jid] + [float(v) for v in p[:3]] + rot

    def model_rot(self, name, rot, fallback):
        """the angles (degrees) of an effect turned rot in the fighter's frame, in the frame of bone `name`'s
        joint at this frame of the script's Ultimate animation. EFFECT_FLW_POS follows the bone's position
        and keeps its angles in the fighter's frame; followed fully (call), the joint's turn at the spawn
        frame is taken out (its turn while the effect lasts stays: Sephiroth's hand turns 0.1 degrees in
        forward air's frames 13 - 17, 6 in up tilt's 20 - 25). Until test 78 the angles were taken in the
        bone's frame: forward air's speed lines (on swordl2, along the blade) stood up instead of lying
        along his swing. fallback: without the animation"""
        import numpy as np
        if self.pose is None or self.anim is None:
            self.unposed += 1
            return fallback
        n = self.joint_bone(name)
        if n == 'top':
            return [float(v) for v in rot]
        m = self.pose.matrix(self.anim, n, int(round(self.frame)))[:3, :3]
        m = m / np.linalg.norm(m, axis=0)[None, :]
        return euler_xyz(m.T @ euler_matrix([float(v) for v in rot]))

    def trail(self, a):
        """AFTER_IMAGE4_ON(_arg29)(agent, tex1, tex2, blur, bone1, x1, y1, z1, bone2, x2, y2, z2,
        terminate, effect, bone3, x, y, z, rx, ry, rz, size, mode, axis, _, blend, ...) -> Sword_Glow"""
        t1, t2 = self.ids.get(a[1]), self.ids.get(a[2])
        if t1 is None or t2 is None:
            for t in (a[1], a[2]):
                if t not in self.ids:
                    self.missing[t] = self.missing.get(t, 0) + 1
            return []
        b1, p1 = self.bone_at(a[4], a[5:8])
        b2, p2 = self.bone_at(a[8], a[9:12])
        b3, p3 = self.bone_at(a[14], a[15:18])
        return [cmd('Sword_Glow', t1, t2, int(float(a[3])), b1, *p1, b2, *p2, int(a[12] in ('true', True)), 0,
                    b3, *p3, *[float(v) for v in a[18:21]], float(a[21]), 0, 0, 0, *TRAIL_BLEND)]

    def call(self, name, a, raw):
        short = name.split('::')[-1]
        if short in ('frame', 'wait'):
            return super().call(name, a, raw)
        if short == 'EFFECT_OFF_KIND':
            eid = self.ids.get(a[1])
            if eid is None:
                self.missing[a[1]] = self.missing.get(a[1], 0) + 1
                return []
            return [cmd('Terminate_Graphic_Effect', eid, int(bool(a[2])), int(bool(a[3])))]
        if short.startswith('AFTER_IMAGE4_ON'):
            return self.trail(a)
        if short == 'AFTER_IMAGE_OFF':
            return [cmd('Terminate_Sword_Glow', int(float(a[1])))]
        if short in LAST_EFFECT:
            # the last effect's handle (EffectModule +0x24 in Ultimate; a trail doesn't set it): left
            # out with that effect when it wasn't converted, or it would land on the one before
            if not self.last:
                return []
            scale = LAST_EFFECT[short]
            vals = [float(v) for v in a[1:]]
            if short == 'LAST_PARTICLE_SET_COLOR' and self.last_name in self.baked:
                return []
            if short == 'LAST_EFFECT_SET_COLOR' and self.last_name in self.tints:
                vals = [v / (t or 1.0) for v, t in zip(vals, self.tints[self.last_name])]
            return [cmd(short, *[v * scale for v in vals])]
        if short == 'EFFECT_DETACH_KIND':
            eid = self.ids.get(a[1])
            if eid is None:
                self.missing[a[1]] = self.missing.get(a[1], 0) + 1
                return []
            return [cmd('EFFECT_DETACH_KIND', eid, int(float(a[2])) & 0xFFFFFFFF)]
        if short not in EFFECT_MACROS and same_name_syntax(short):
            # Smash 4's command of the same name, flips included: they mirror the effect when facing left
            # as Ultimate's do (until Squirtle's effects test 25 a _FLIP macro became the plain one, which
            # only turns it with the facing: his forward tilt's arc, turned (0, -30, 195), swung the wrong way
            # facing left; _FLIP_ALPHA / _RND ones were dropped: up tilt's speed line, the aerials' winds)
            return self.same_name(short, a)
        if short not in EFFECT_MACROS:
            self.skip(short)
            return []
        target, shape = EFFECT_MACROS[short]
        if shape == 'global':
            # no bone: a place in the world (Smash 4's EFFECT_GLOBAL); Ultimate's last bool (its terminate) dropped
            eid = self.ids.get(a[1])
            self.last, self.last_name = eid is not None, a[1]
            if eid is None:
                if a[1] != 'null':
                    self.missing[a[1]] = self.missing.get(a[1], 0) + 1
                return []
            return [cmd(target, eid, *[float(v) for v in a[2:9]])]
        if short.startswith('EFFECT_FLW_POS') and any(abs(float(v)) > 1e-6 for v in a[3:6]):
            # Smash 4's position-only follow adds the offset unturned to the bone's position
            # (cross_f.rpx 0x0334E4B0: effect record +0x144 bit 0x1000), Ultimate turns it with the
            # bone (down air's flash 22 along the blade sat above his head): follow fully instead, its angles
            # (Ultimate's in the fighter's frame) taken into the joint's at the spawn frame (model_rot)
            target = 'External_Graphic' if short == 'EFFECT_FLW_POS' else 'Graphic_Effect4'
        if target == 'Graphic_Effect4' and a[1] in self.turned_off:
            # a NO_STOP effect its own script turns off: the plain follow (killed with the motion
            # too), or a script cut before the EFFECT_OFF_KIND (forward air landing early) leaves an
            # endless emitter on for good (Graphic_Effect4: EffectModule 0x271A, no 0x8000 flag)
            target = 'External_Graphic'
        eid = self.ids.get(a[1])
        if eid is None and a[1] == 'null' and target == 'Graphic_Effect':
            # FOOT_EFFECT("null"): the ground's own footstep effect (dust, grass, water by the stage's material); Smash 4
            # writes it as effect 0 on the foot (vanilla ZSS's walks: Graphic_Effect(0, LFootJ / RFootJ)). Left out up to
            # Byleth v5 (no step dust in his walks, turn, dash, run)
            eid = 0
        self.last = eid is not None
        self.last_name = a[1]
        if eid is None:
            if a[1] != 'null':
                self.missing[a[1]] = self.missing.get(a[1], 0) + 1
            return []
        bone, *place = self.place(a[2], a[3:6], a[6:9])
        if short.startswith('EFFECT_FLW_POS') and target != EFFECT_MACROS[short][0]:
            place[3:6] = self.model_rot(a[2], a[6:9], place[3:6])
        place.append(float(a[9]))                               # x, y, z, rx, ry, rz, size
        if shape.startswith('full'):
            rest = [float(v) for v in a[10:16]] + [int(bool(a[16]))]
            extra = a[17:]
        else:
            rest = [int(bool(a[10]))]
            extra = a[11:]
        if shape.endswith('+alpha'):
            rest.append(float(extra[0]) * 100.0)
        elif shape.endswith('+color'):
            # not capped at 255: vanilla passes more (Falco 714 / 76 / 280); capping one channel shifts
            # the hue (his jab tint (0.75, 0.5, 1.5) drew pink as (191, 127, 255), test 51)
            rest += [float(v) * 255.0 for v in extra[:3]]
        return [cmd(target, eid, bone, *place, *rest)]


def _same_name(self, short, a):
    """an Ultimate effect macro -> Smash 4's command of the same name, argument by argument (same_name_syntax)"""
    target, syn = same_name_syntax(short)
    if short == 'EFFECT_FOLLOW_NO_STOP_FLIP' and a[1] in self.turned_off:
        target, syn = same_name_syntax('EFFECT_FOLLOW_FLIP')       # as EFFECT_FOLLOW_NO_STOP (call)
    args, out, i = a[1:], [], 0
    if len(args) != len(syn):
        self.skip(short + ' (arguments)')
        self.last = False
        return []
    self.last, self.last_name = True, args[0]
    k = 0
    while k < len(syn):
        f, v = syn[k], args[k]
        if f in ('Graphic', 'GFXRight', 'GFXLeft', 'Effect'):
            eid = self.ids.get(v)
            if eid is None:
                if v != 'null':
                    self.missing[v] = self.missing.get(v, 0) + 1
                self.last = False
                return []
            out.append(eid)
        elif f == 'Bone':
            if syn[k + 1:k + 7] != ['X', 'Y', 'Z', 'XRot', 'YRot', 'ZRot']:
                self.skip(short + ' (layout)')
                self.last = False
                return []
            out += self.place(v, args[k + 1:k + 4], args[k + 4:k + 7])
            k += 7
            continue
        elif f == 'Terminate':
            out.append(int(bool(v)))
        elif f == 'FlipType':
            out.append(FLIP_TYPES.get(v, 0) if isinstance(v, str) else int(v))
        elif f == 'Alpha':
            out.append(float(v) * 100.0)
        elif f in ('Red', 'Green', 'Blue'):
            out.append(float(v) * 255.0)
        elif f == 'Size' or f.startswith('Random'):
            out.append(float(v))
        else:
            self.skip(short + ' (' + f + ')')
            self.last = False
            return []
        k += 1
    return [cmd(target, *out)]


EffectTranslator.same_name = _same_name


class BonePose:
    """an Ultimate skeleton's bones under its animations: model-space transforms (4 x 4, column vectors) at a
    frame, each bone's animated local transform (its rest one without a track) composed up its chain"""

    def __init__(self, nusktb):
        import ssbh_data_py as s
        self.skel = s.skel_data.read_skel(nusktb)
        self.bones = {b.name.lower(): b for b in self.skel.bones}
        self.tracks = {}

    def anim(self, path):
        if path not in self.tracks:
            import ssbh_data_py as s
            t = {}
            for g in s.anim_data.read_anim(path).groups:
                if g.group_type.name == 'Transform':
                    for n in g.nodes:
                        for tr in n.tracks:
                            t[n.name.lower()] = tr.values
            self.tracks[path] = t
        return self.tracks[path]

    def matrix(self, path, bone, frame):
        import numpy as np
        tracks = self.anim(path)
        b, m = self.bones[bone.lower()], np.eye(4)
        while b is not None:
            vals = tracks.get(b.name.lower())
            if vals:
                v = vals[max(0, min(frame, len(vals) - 1))]
                x, y, z, w = v.rotation
                local = np.eye(4)
                local[:3, :3] = np.array([
                    [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                    [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                    [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]) * np.array(v.scale)[None, :]
                local[:3, 3] = v.translation
            else:
                local = np.array(b.transform, float).T      # ssbh's rows: translation in the last
            m = local @ m
            b = self.skel.bones[b.parent_index] if b.parent_index is not None else None
        return m


def script_anims(motion_list):
    """{hash40 of a script name (game_ / effect_ / sound_ / expression_...): its motion's first animation file}
    from Ultimate's motion_list.bin (the animations beside it)"""
    d = os.path.dirname(motion_list)
    files = {hash40(f): os.path.join(d, f) for f in os.listdir(d) if f.endswith('.nuanmb')}
    out = {}
    for e in read_motion_list(motion_list):
        path = next((files[h] for h in e['anims'] if h in files), None)
        if path:
            for h in (e['game'],) + e['scripts']:
                out.setdefault(h, path)
    return out


def translate_effects(scripts_dir, effect_bin, joints, ids, parents, skip=('special', 'final'), locals_=None,
                      tints=None, baked=None, nusktb=None, motion_list=None, motions=()):
    """every effect_* function of the dump -> the effect script of the same Smash 4 name (TRANSLATE's
    for the translated moves), replacing the base's (its own effects, e.g. Zelda's sparkles); not the
    moves still the base's (specials, Final Smash). Returns {Smash 4 name: commands}, {missing name:
    count}"""
    global EFFECT_CONDS
    # the facing-left branch: in the dumps the facing-right one is often nested inside it (a misplaced
    # else), so it's the one that always holds the effect; Smash 4 places effects by the bones anyway
    EFFECT_CONDS = (LR_LEFT,)
    # Ultimate turns an effect on top with the facing and mirrors nothing: an asymmetric one has a
    # mirrored _r copy that the script picks when facing right (Squirtle's water_smash / _r, water_cutter
    # / _r, with mirrored angles). Smash 4 turns top's effects with the facing too (effect_variants.py), so
    # the choice is made in game (LR_FACING) wherever fix_lr_split could lay the split out; elsewhere the
    # facing-left branch, as before. Until Squirtle's effects test 9 it was always the facing-left one: his
    # forward smash wave curled up over him facing right instead of running along the ground
    DYNAMIC_CONDS[LR_TAG] = LR_FACING
    tr = EffectTranslator(joints, ids, parents, locals_, tints, baked)
    anims = {}
    if nusktb and motion_list:
        tr.pose, anims = BonePose(nusktb), script_anims(motion_list)
    out = {}
    for path in sorted(os.listdir(scripts_dir)):
        if not path.endswith('.txt'):
            continue
        src = path[:-4]
        for fn, body in functions(open(os.path.join(scripts_dir, path)).read()).items():
            if not fn.startswith('effect_'):
                continue
            name = fn[len('effect_'):]
            if name == src.lower():
                name = TRANSLATE.get(src, name)
            # (motions: the motion table's crcs, as for sound: a slot the base's effect file has no script for still
            # gets Ultimate's: Byleth's taunts, ZSS having no taunt effects)
            if name not in TRANSLATE.values() and (name.startswith(skip) or (acmd.crc(name) not in effect_bin.scripts
                                                                          and acmd.crc(name) not in motions)):
                continue
            tr.last, tr.last_name = False, None
            tr.anim = anims.get(hash40(fn)) or anims.get(hash40('game_' + fn[len('effect_'):]))
            tr.turned_off = set(re.findall(r'EFFECT_OFF_KIND\(agent, Hash40::new\("([^"]+)"', body))
            cmds = self_jump(tr.script(body), name)
            # looping motions: the base's script ends Loop_Rest, JUMP(itself); Ultimate re-runs its own
            base = [c.name for c in effect_bin.scripts.get(acmd.crc(name), [])]
            if 'Loop_Rest' in base and not any(c.name == 'JUMP' for c in cmds):
                cmds = cmds[:-1] + [cmd('Loop_Rest'), cmd('JUMP', acmd.crc(name)), acmd.Command(acmd.END)]
            out[name] = cmds
    EFFECT_CONDS = ()
    DYNAMIC_CONDS.pop(LR_TAG, None)
    if tr.unposed:
        print('%d position-following effects without their animation: angles taken in the bone\'s frame' % tr.unposed)
    return out, tr.missing


class SoundTranslator(Translator):
    """sound_* functions -> Smash 4 sound scripts. ids: Ultimate name (se_ / vc_ / seq_, lower case) -> Smash
    4 sound id (tools/ultimate_sound.py's sound_ids.json, the fighter's own banks and sequences) and the
    common sounds (reference/ultimate_sound_map.json "common_se"); other names are left out and counted.
    The commands are Smash 4's of the same macro (crc32 of the macro name = the ACMD id)."""
    SAME = {'PLAY_SE': 'Sound_Effect', 'STOP_SE': 'Stop_Sound_Effect', 'PLAY_STEP': 'Sound_Effect2',
            'PLAY_LANDING_SE': 'Sound_Effect3', 'PLAY_DOWN_SE': 'Sound_Effect4', 'PLAY_STATUS': 'Transient_Sound_Effect',
            'PLAY_SEQUENCE': 'Low_Voice_Clip', 'PLAY_SE_NO_3D': 'PLAY_SE_NO_3D', 'PLAY_SE_REMAIN': 'PLAY_SE_REMAIN',
            'SET_TAKEOUT_SE': 'SET_TAKEOUT_SE', 'STOP_SE_STATUS': 'STOP_SE_STATUS'}

    def __init__(self, ids, fail=None):
        super().__init__({})
        self.ids, self.missing = ids, {}
        self.loop = False
        self.fail = fail or {}          # --fail-sounds: {condition: sounds of its failed branch}
        self.drop = set()
        self.extra_fixes = (fix_trailing_flag_else,)

    def sid(self, name):
        v = self.ids.get(name.lower()) if isinstance(name, str) else None
        if v is None and isinstance(name, str):
            # a random container of numbered tones (Byleth's se_master_attack100: _01 - _03, one picked each hit): its
            # tones take turns in Ultimate; Smash 4's ACMD has no pick, so its first tone (as ultimate_sound.py's aliases)
            v = self.ids.get(name.lower() + '_01')
        if v is None:
            self.missing[name] = self.missing.get(name, 0) + 1
        return v

    def call(self, name, a, raw):
        short = name.split('::')[-1]
        if short in ('frame', 'wait'):
            return super().call(name, a, raw)
        if short == 'wait_loop_sync_mot':
            self.loop = True
            return []
        if short in self.SAME and isinstance(a[1], str) and a[1].lower() in self.drop:
            return []
        if short in self.SAME:
            v = self.sid(a[1])
            return [] if v is None else [cmd(self.SAME[short], v)]
        if short in ('PLAY_FLY_VOICE', 'PLAY_STEP_FLIPPABLE'):
            v = [self.sid(x) for x in a[1:3]]
            return [] if None in v else [cmd(short, *v)]
        if short == 'SET_PLAY_INHIVIT':
            v = self.sid(a[1])
            return [] if v is None else [cmd('SET_PLAY_INHIVIT', v, int(float(a[2])))]
        self.skip(short)
        return []


# Smash 4's rumble kinds (param/pad_rumble/rumble_pattern_data*.bin: a param list per kind of (op, value): 1 on / 2 off
# / 3 brake for n frames, 4 loop n times (8000: for good) ... 5 loop end, 0 end) whose pattern never ends (an 8000
# loop: 2, 3, 8, 9, 26, 34, 35, 36) or runs 1000 frames (6), on the Wii U GamePad and Pro controller alike. Vanilla
# plays them as Rumble_Loop (tied to the status: 1328 times) and almost never as a plain Rumble (27); Smash 4 has no
# stop command for an Ultimate rbkind_erase
RUMBLE_ENDLESS = (2, 3, 6, 8, 9, 26, 34, 35, 36)


class ExpressionTranslator(Translator):
    """expression_* functions -> Smash 4 expression scripts (rumble, camera quake, slope, item visibility),
    reference/ultimate_sound_map.json: ControlModule::set_rumble -> Rumble (RUMBLE) or Rumble_Loop
    (RUMBLE_STATUS: the length carried when Ultimate loops it) by kind; RUMBLE_HIT (on hit only) has no
    Smash 4 form: vanilla rumbles once per swing, so it's dropped when the script rumbles anyway, else
    played as a plain one; slope! -> SLOPE / Slope_Full (SLOPE_INTP) / Slope_Full2 (its 4-argument form);
    QUAKE -> QUAKE by size; the common helpers (expression_LandingHeavyRumble...) -> what vanilla plays."""

    def __init__(self, table):
        super().__init__({})
        self.t, self.missing = table, {}
        self.loop = False
        self.has_rumble = False

    def rumble(self, kind, n, loop):
        k = self.t['rumble'].get(kind)
        if k is None:
            self.missing[kind] = self.missing.get(kind, 0) + 1
            return []
        # a Smash 4 kind whose pattern never ends (or runs 1000 frames) only as Rumble_Loop, which the status's end
        # stops: as plain Rumble it ran on for seconds (Squirtle's up smash, rbkind_loopattack -> 8, test 25)
        status = k[0] == 'RUMBLE_STATUS' or int(k[1]) in RUMBLE_ENDLESS
        return [cmd('Rumble_Loop' if status else 'Rumble', k[1], int(float(n)) if status and loop else 0)]

    def call(self, name, a, raw):
        short = name.split('::')[-1]
        if short in ('frame', 'wait'):
            return super().call(name, a, raw)
        if short == 'wait_loop_sync_mot':
            self.loop = True
            return []
        if name in ('ControlModule::set_rumble', 'RUMBLE_FINAL_TARGET') or short == 'RUMBLE_FINAL_TARGET':
            if short == 'RUMBLE_FINAL_TARGET':
                return self.rumble(a[1], 0, False)
            return self.rumble(a[1], a[2], bool(a[3]))
        if short == 'RUMBLE_HIT':
            return [] if self.has_rumble else self.rumble(a[1], 0, False)
        if short == 'slope!':
            st = self.t['slope_status'][str(a[2]).replace('SLOPE_STATUS_', '')]
            if str(a[1]).endswith('SLOPE_INTP'):
                if len(a) > 4 and a[4] is True:
                    return [cmd('Slope_Full2', st, int(float(a[3])), 1)]
                return [cmd('Slope_Full', st, int(float(a[3])))]
            return [cmd('SLOPE', st)]
        if short == 'QUAKE':
            k = self.t['quake'].get(str(a[1]).replace('CAMERA_QUAKE_KIND_', ''))
            return [] if k is None else [cmd('QUAKE', k[0])]
        if short == 'FT_ATTACK_ABS_CAMERA_QUAKE':
            return [cmd('FT_ATTACK_ABS_CAMERA_QUAKE', 0, 0)]
        if name == 'ItemModule::set_have_item_visibility':
            return [cmd('Item_Visibility', int(bool(a[1])))]
        m = re.search(r'expression_(\w+Rumble)$', name)
        if m:
            out = []
            for c in self.t['rumble_helpers'].get(m.group(1), []):
                k = re.match(r'(\w+)\(Kind=(\d+), (\d+)\)', c)
                out.append(cmd('Rumble_Loop' if k.group(1) == 'RUMBLE_STATUS' else 'Rumble', int(k.group(2)),
                               int(k.group(3))))
            return out
        self.skip(short)
        return []


def first_voice_region(body):
    """the dump's sound scripts with Ultimate's voice-region chain (a spell shout per language): its first
    block (English: the _en sequences); the chain's own first `if` is lost in the dump, leaving a stray
    `} else {` at the left margin"""
    i = body.find('\n}\nelse {')
    return body[:i] if i >= 0 and 'GET_VOICE_REGION' in body[i:] else body


# the dump's decompiled tests (`WorkModule::is_flag(agent.module_accessor, *F); if(...operator==(...)(false, B)){`,
# Sephiroth's: the flag in the statement before, the `if` only compares) folded into the plain `if [!]is_flag(F) {`
# form, so --cond / --sound-cond see the flag's name; and `macros::IS_RANDOM(agent, N); if(...(false, true)){`
# into `if IS_RANDOM_CHANCE(N) {`: Smash 4's own IS_RANDOM(Chance=N) True(...) (Zelda's cliff catch voice)
_EQ = r'if\(methodlib::L2CValue::operator==\(lib::L2CValueconst&\)const\(false, (true|false)\)\)\{'
FLAG_TEST_RE = re.compile(r'WorkModule::is_flag\(agent\.module_accessor, \*(\w+)\);(\s*)' + _EQ)
RANDOM_TEST_RE = re.compile(r'macros::IS_RANDOM\(agent, (\d+)\);(\s*)' + _EQ)


def _block_end(s, i):
    """the index of the '}' closing the '{' at s[i]"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                return j
    return -1


VOICE_IF = re.compile(r'if macros::GET_VOICE_VARIATION\(agent\) == (\d+) \{')
VOICE_ELIF = re.compile(r'\s*else if macros::GET_VOICE_VARIATION\(agent\) == (\d+) \{')


def fold_voice_variation(body):
    """Ultimate's per-costume chains (`if GET_VOICE_VARIATION(agent) == 0 {..} else if .. == 1 {..} ... == 7`: Byleth's
    taunts / wins, the male and female timings alternating) -> one costume-parity test (the even costumes' block, else
    the odd ones'), which the translator decides in game (COLOR_PARITY); a chain whose even (or odd) blocks differ
    keeps costume 0's block (and is counted). Before: every branch was false, so those scripts were empty"""
    out, i = '', 0
    while True:
        m = VOICE_IF.search(body, i)
        if not m:
            return out + body[i:]
        blocks, j = {}, m.end() - 1
        k = int(m.group(1))
        while True:
            e = _block_end(body, j)
            if e < 0:
                return out + body[i:]
            blocks[k] = body[j + 1:e]
            n = VOICE_ELIF.match(body, e + 1)
            if not n:
                break
            k, j = int(n.group(1)), n.end() - 1
        norm = {k: re.sub(r'\s+', ' ', v).strip() for k, v in blocks.items()}
        even = [norm[k] for k in sorted(norm) if k % 2 == 0]
        odd = [norm[k] for k in sorted(norm) if k % 2]
        if even and odd and len(set(even)) == 1 and len(set(odd)) == 1:
            ev, od = blocks[min(k for k in blocks if k % 2 == 0)], blocks[min(k for k in blocks if k % 2)]
            rep = ('{%s}' % ev if norm[min(blocks)] == odd[0] and even[0] == odd[0] else
                   'if WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) %% 2 == 0 {%s}'
                   ' else {%s}' % (ev, od))
        else:
            rep = '{%s}' % blocks.get(0, blocks[min(blocks)])
            VOICE_KEPT.append(len(blocks))
        out += body[i:m.start()] + rep
        i = e + 1


VOICE_KEPT = []     # chains that couldn't be folded into a parity test (costume 0's block kept)


def fold_tests(body):
    body = FLAG_TEST_RE.sub(lambda m: '%sif %sWorkModule::is_flag(boma, *%s) {' % (
        m.group(2), '' if m.group(3) == 'true' else '!', m.group(1)), body)
    return RANDOM_TEST_RE.sub(lambda m: m.group(0) if m.group(3) == 'false' else      # (a lost pick: left as is)
                              '%sif IS_RANDOM_CHANCE(%s) {' % (m.group(2), m.group(1)), body)


# Ultimate sound script -> Smash 4's of the same move where the names differ (Smash 4's ledge has quick / slow
# forms; the base's motion table holds the quick ones: Zelda has no slow climb / escape / jump)
SOUND_NAMES = {'cliffclimb': 'cliffclimbquick', 'cliffescape': 'cliffescapequick', 'cliffjump1': 'cliffjumpquick1',
               'cliffjump2': 'cliffjumpquick2'}
# Ultimate's results voice is a script of its own (WinNA; WinNB the line against one rival: Sephiroth's against
# Cloud): merged into WinN's sound script, which Smash 4's results play
SOUND_MERGE = {'win1a': 'win1', 'win2a': 'win2', 'win3a': 'win3'}


def merge_flat(a, b):
    """two scripts of FRAME / WAIT and plain commands as one (each command at its frame); None if either branches"""
    def timed(sc):
        t, out = 0, []
        for c in sc:
            if c.ident == acmd.END:
                break
            if c.name in ('True', 'Else', 'Loop_Rest', 'JUMP', 'Goto', 'Int_Var_Compare', 'Float_Var_Compare',
                          'IS_RANDOM'):
                return None
            if c.name == 'FRAME':
                t = max(t, int(c.params[0]))
            elif c.name == 'WAIT':
                t += int(c.params[0])
            else:
                out.append((t, c))
        return out
    ta, tb = timed(a), timed(b)
    if ta is None or tb is None:
        return None
    out, t = [], 0
    for when, c in sorted(ta + tb, key=lambda x: x[0]):
        if when > t:
            out.append(cmd('FRAME', when))
            t = when
        out.append(c)
    return out + [acmd.Command(acmd.END)]


def translate_others(kind, scripts_dir, base_bin, tr, skip=('special', 'final'), motions=()):
    """every sound_* / expression_* function (kind) of the dump -> the script of the same Smash 4 name, as
    translate_effects; a looping one (wait_loop_sync_mot) ends Loop_Rest, JUMP(itself) as vanilla's do.
    Sound: also the scripts of the base's motion table that its sound file has none for (motions: their crcs;
    Zelda has no third taunt / results-wait sounds), SOUND_NAMES' names, SOUND_MERGE's results voices"""
    out = {}
    for path in sorted(os.listdir(scripts_dir)):
        if not path.endswith('.txt'):
            continue
        src = path[:-4]
        for fn, body in functions(open(os.path.join(scripts_dir, path)).read()).items():
            if not fn.startswith(kind + '_'):
                continue
            name = fn[len(kind) + 1:]
            if name == src.lower():
                name = TRANSLATE.get(src, name)
            if kind == 'sound':
                name = SOUND_NAMES.get(name, name)
            known = acmd.crc(name) in base_bin.scripts or (kind == 'sound' and (
                acmd.crc(name) in motions or name in SOUND_MERGE))
            if name not in TRANSLATE.values() and (name.startswith(skip) or not known):
                continue
            tr.loop = False
            tr.has_rumble = 'set_rumble' in body
            tr.drop = set(n for k, v in getattr(tr, 'fail', {}).items() if k in body for n in v)
            cmds = self_jump(tr.script(fold_voice_variation(fold_tests(first_voice_region(body)) if kind == 'sound'
                                                            else body)), name)
            if tr.loop and not any(c.name == 'JUMP' for c in cmds):
                cmds = cmds[:-1] + [cmd('Loop_Rest'), cmd('JUMP', acmd.crc(name)), acmd.Command(acmd.END)]
            out[name] = cmds
    if kind == 'sound':
        for src, dst in SOUND_MERGE.items():
            if src in out:
                base = out.get(dst) or (base_bin.scripts.get(acmd.crc(dst)) if acmd.crc(dst) in motions else None)
                merged = merge_flat(base, out[src]) if base is not None else None
                if merged is not None:
                    out[dst] = merged
                del out[src]
    return out


def mtable_crcs(path):
    """the motion crcs of a motion.mtable (big-endian words)"""
    d = open(path, 'rb').read()
    return set(struct.unpack('>%dI' % (len(d) // 4), d[:len(d) // 4 * 4]))


def skeleton_locals(nusktb):
    """{bone (lower case): its local transform (4 x 4, row vectors: translation in the 4th row)}"""
    import numpy as np
    import ssbh_data_py as s
    return {b.name.lower(): np.array(b.transform, float) for b in s.skel_data.read_skel(nusktb).bones}


def skeleton_parents(nusktb):
    import ssbh_data_py as s
    sk = s.skel_data.read_skel(nusktb)
    return {b.name.lower(): sk.bones[b.parent_index].name.lower() for b in sk.bones
            if b.parent_index is not None and b.parent_index >= 0}


# ---------------------------------------------------------------- joints
def joint_ids(model_dir):
    """Ultimate bone name (lower case) -> ACMD joint ID, from the converted model's vbn + jtb (the
    standard bones by their Smash 4 names, the rest by their own)"""
    import ultimate_fighter as U
    vbn = U.read_vbn(os.path.join(model_dir, 'model.vbn'))
    d = open(os.path.join(model_dir, 'model.jtb'), 'rb').read()
    n1, n2 = struct.unpack('>HH', d[:4])
    table0 = struct.unpack('>%dh' % n1, d[4:4 + 2 * n1])
    table1 = struct.unpack('>%dh' % n2, d[4 + 2 * n1:4 + 2 * (n1 + n2)])
    s4_to_ult = {s: u for s, u in U.STANDARD}
    out = {}
    # table 1 (IDs 1000 + k): the base's own (FaceN...) and model --joints' (Squirtle's tail); table 0's win
    for k in range(n2 - 1, -1, -1):
        out[vbn[table1[k]][0].lower()] = 1000 + k
    for jid in range(n1, 0, -1):
        name = vbn[table0[jid - 1]][0]
        out[s4_to_ult.get(name, name).lower()] = jid
    return out


# ---------------------------------------------------------------- motion_list.bin (Ultimate)
def hash40(s):
    return zlib.crc32(s.encode()) | (len(s) << 32)


def read_motion_list(path):
    """[{key, game, flags, blend, anims, scripts, extra}] (extra = xlu start, xlu end, cancel frame,
    no-stop-interpolation bytes, when present)"""
    d = open(path, 'rb').read()
    _magic, _id, n = struct.unpack_from('<QQQ', d, 0)
    o, out = 24, []
    for _ in range(n):
        key, game, flags, blend, nanim, size = struct.unpack_from('<QQHBBI', d, o)
        o += 24
        anims = struct.unpack_from('<%dQ' % nanim, d, o)
        o += 8 * nanim + (nanim + 3) // 4 * 4          # then one byte per animation, padded to 4
        scripts = struct.unpack_from('<%dQ' % (size // 8), d, o)
        o += 8 * (size // 8)
        extra = d[o:o + size % 8]
        o += size % 8
        out.append(dict(key=key, game=game, flags=flags, blend=blend, anims=anims, scripts=scripts, extra=extra))
    assert o == len(d), 'motion_list: %d of %d bytes read' % (o, len(d))
    return out


def motion_frames(args, done):
    """vl group 1 bytes / motion.mtable entries of the translated motions; returns {index: move flag}"""
    import mtable
    import fighter_param_vl as V
    ml = read_motion_list(args.motion_list)
    mt = list(struct.unpack('>%dI' % (os.path.getsize(args.mtable[0]) // 4), open(args.mtable[0], 'rb').read()))
    vf = V.load(args.vl[0], args.vl_kind)
    common = {c.lower(): i for i, c in enumerate(mtable.COMMON)}

    def byte(i, k, v=None):
        (_p, t), = V.find(vf, 'm0[%d].%d' % (i, k), '0', {})
        if v is not None:
            t.set(v)
        return t.value
    moves = {}
    for src, name in done:
        if name.startswith('landing') or name in GAME_ONLY:   # landing lag: fighter_param's landing frames
            continue
        h = acmd.crc(name)
        if name in SLOTS:                       # --translate: a motion slot of its own (a custom-move slot)
            i = SLOTS[name]
            if mt[i] != h:
                mt[i] = h
                byte(i, 0, 1)
        elif h in mt:
            i = mt.index(h)
        else:
            i = common[name]
            assert mt[i] == 0, 'motion 0x%X has another script' % i
            mt[i] = h
            byte(i, 0, 1)
        ent = [e for e in ml if hash40('game_' + src.lower()) in (e['game'],) + e['scripts']]
        if not ent or len(ent[0]['extra']) < 3:
            print('  %s: no motion_list entry / frames' % name)
            continue
        if ent[0]['flags'] & 2 and byte(i, 0):
            # Ultimate's loop flag (motion_list 0x2): byte 0 is 0 on looping motions (Hero's
            # SpecialLwSelect, a new slot, held its last frame)
            byte(i, 0, 0)
            print('  0x%03X %-16s loops' % (i, name))
        xs, xe, cancel = ent[0]['extra'][:3]
        for k, v in ((2, cancel), (3, xs), (4, xe)):
            byte(i, k, v)
        moves[i] = (name, ent[0]['flags'] & 4)
        print('  0x%03X %-16s cancel %2d, intangible %d-%d, move %d' % (i, name, cancel, xs, xe, bool(ent[0]['flags'] & 4)))
    # motions whose scripts aren't translated but whose cancel frame is the move's (the taunts: Ultimate's
    # appeal_* cancel 50; Zelda's 80 - 110 stayed on Sephiroth to test 72, port_check C1): byte 2 alone
    for name in CANCEL_ONLY:
        h = acmd.crc(name)
        ent = [e for e in ml if hash40('game_' + name) in (e['game'],) + e['scripts']]
        if h not in mt or not ent or len(ent[0]['extra']) < 3:
            continue
        i = mt.index(h)
        if byte(i, 2) != ent[0]['extra'][2]:
            print('  0x%03X %-16s cancel %2d (was %d)' % (i, name, ent[0]['extra'][2], byte(i, 2)))
            byte(i, 2, ent[0]['extra'][2])
    import ultimate_vl_blend
    ultimate_vl_blend.apply_blends(vf, ml)      # Ultimate's blend into each common motion (byte 1)
    open(args.mtable[1], 'wb').write(struct.pack('>%dI' % len(mt), *mt))
    open(args.vl[1], 'wb').write(vf.build())
    return moves


def common_to_own(o, translated, ids, own_ids_path):
    """in the base's effect scripts the port keeps (no Ultimate script for them: ledge quick options,
    sleep...), each Smash 4 common effect that stands for an Ultimate sys_* effect the port converted
    (its ids file: vfxb_to_ptcl.py --extra-eff) becomes that one, so they match his own moves (port_check E3)"""
    s4 = {k: int(v, 0) for k, v in json.load(open(os.path.join(HERE, '..', 'reference', 'ultimate_sys_effects.json'))).items()
          if not k.startswith('_')}
    own = {k for k in json.load(open(own_ids_path)) if k.startswith('sys_') and '@' not in k}
    to = {}
    for name in sorted(own):
        if name in s4 and name in ids:
            to.setdefault(s4[name], ids[name])
    n = 0
    for h, cmds in o.scripts.items():
        if h in translated:
            continue
        for c in cmds:
            syn = (acmd.INFO.get(c.ident) or {}).get('syntax', [])
            if syn[:1] == ['Graphic'] and c.params and c.params[0] in to:
                c.params[0] = to[c.params[0]]
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scripts')
    ap.add_argument('game_bin')
    ap.add_argument('out')
    ap.add_argument('model_dir')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--others', nargs=2, metavar=('IN_DIR', 'OUT_DIR'))
    ap.add_argument('--motion-list')
    ap.add_argument('--mtable', nargs=2, metavar=('IN', 'OUT'))
    ap.add_argument('--vl', nargs=2, metavar=('IN', 'OUT'))
    ap.add_argument('--vl-kind', default='zelda', help='the vl file\'s layout (the base fighter)')
    ap.add_argument('--base-rpx', help='with --motion-list: an executable to compare the move flags with')
    ap.add_argument('--base-kind', type=lambda v: int(v, 0))
    ap.add_argument('--have', help='LEFT,RIGHT as the model was built with (ultimate_fighter.py --have)')
    ap.add_argument('--effects', nargs=2, metavar=('IDS_JSON', 'NUSKTB'),
                    help='with --others: translate the effect scripts too (IDS_JSON: Ultimate effect name -> '
                         'Smash 4 id, e.g. reference/ultimate_sys_effects.json, comma-separated files merged; trail '
                         'texture names -> trail ids too; NUSKTB: Ultimate skeleton)')
    ap.add_argument('--sound-ids', help='with --others: translate the sound scripts too (JSON: Ultimate sound name -> '
                    'Smash 4 id, tools/ultimate_sound.py\'s sound_ids.json; comma-separated files merged; the '
                    'common sounds come from reference/ultimate_sound_map.json)')
    ap.add_argument('--fail-sounds', action='append', default=[], metavar='SUBSTRING=NAME,NAME',
                    help='with --sound-ids: in sound scripts testing that condition (one taken as true, --cond), '
                    'these sounds are its failed branch\'s (the dump loses those braces): left out (Hero: '
                    'SUCCESS_SP=se_brave_miss,vc_brave_mp_lost; a cast he can\'t pay for is SpecialLwFail)')
    ap.add_argument('--expressions', action='store_true', help='with --others: translate the expression scripts '
                    '(rumble, quake, slope, item visibility: reference/ultimate_sound_map.json)')
    ap.add_argument('--translate', help='JSON {Ultimate file: Smash 4 name or {"name", "slot"}}: more scripts for '
                    'this run (e.g. a fighter\'s specials; names starting with "special" are kept), a "slot" '
                    'naming the motion whose motion.mtable entry gets the new name (empty scripts when the dump '
                    'has none for it)')
    ap.add_argument('--sound-cond', action='append', default=[], help='with --sound-ids: a condition taken as true '
                    'in the sound scripts only (substring, as --cond; Sephiroth: his down smash\'s floor hit '
                    'FLAG_IS_HIT_FLOOR, Scintilla\'s counter FLAG_IS_HIT_SHIELD); repeatable')
    ap.add_argument('--cond', action='append', default=[], help='a condition taken as true (substring of the '
                    'dump\'s condition, e.g. MATERIAL_KIND_IRON) for Steve\'s tool material); repeatable')
    ap.add_argument('--dyn-cond', action='append', default=[], metavar='SUBSTRING=VAR',
                    help="a condition decided in game: the if / else kept as Int_Var_Compare(VAR != 0) True / Else "
                         "(e.g. FLAG_CRITICAL_HIT=0x1000009A, Hero's critical hit); repeatable")
    ap.add_argument('--vec-targets', metavar='OUT_JSON', help='write the translated scripts\' set_vec_target_pos '
                    '(Ultimate\'s "carry the hit fighter to a point": no Smash 4 hitbox field) for the MSC pull, '
                    'tools/vec_target.py msc')
    ap.add_argument('--hold-angle', action='store_true', help='holding multi-hits (Ultimate\'s setoff off + 361 + a '
                    'small knockback: rapid jabs) at HOLD_ANGLE, v17\'s workaround, for an executable without '
                    'tools/hitbox_hold_cave.py; the default is Ultimate\'s angle + Hitbox_Hold (exe_v46y_hold)')
    ap.add_argument('--slot-moves', default='', help='comma-separated SLOT_MOVES (Ultimate file names, e.g. '
                    'Attack100Start,Attack100,Attack100End,AttackS4Hi,AttackS4Lw) to translate: common moves the '
                    'port gave motion slots of their own (port.json motions.add, extra_kinds.json "motions")')
    a = ap.parse_args()
    global HOLD_MODE
    if a.hold_angle:
        HOLD_MODE = 'angle'
    for src in filter(None, a.slot_moves.split(',')):
        TRANSLATE[src] = SLOT_MOVES[src]
    TRUE_CONDS[:] = a.cond
    for d in a.dyn_cond:
        k, v = d.split('=')
        DYNAMIC_CONDS[k] = int(v, 0)
    if a.translate:
        for src, v in json.load(open(a.translate)).items():
            if src.startswith('_'):
                continue
            name = v['name'] if isinstance(v, dict) else v
            TRANSLATE[src] = name
            if isinstance(v, dict) and 'slot' in v:
                SLOTS[name] = int(v['slot'], 0)
    f = acmd.ACMDFile.load(a.game_bin)
    if a.have:
        import ultimate_fighter as U
        U.set_have(*a.have.split(','))
    tr = Translator(joint_ids(a.model_dir))
    done = []
    vec = {}
    for src, name in TRANSLATE.items():
        if a.only and src not in a.only:
            continue
        path = os.path.join(a.scripts, src + '.txt')
        body = None
        if os.path.exists(path):
            body = functions(open(path).read()).get('game_' + src.lower())
        elif name in FALLBACK and os.path.exists(os.path.join(a.scripts, FALLBACK[name] + '.txt')):
            body = functions(open(os.path.join(a.scripts, FALLBACK[name] + '.txt')).read()).get(
                'game_' + FALLBACK[name].lower())
        if body is None and name not in SLOTS:
            if name in EMPTY_IF_ABSENT and not a.only:
                f.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
            continue
        tr.skipped = {}
        # a slot of ours with no game script in the dump (SpecialNCancel): empty scripts, so the
        # slot's base move (a custom-move variant) doesn't run on it
        cmds = self_jump(tr.script(body), name) if body is not None else [acmd.Command(acmd.END)]
        f.scripts[acmd.crc(name)] = cmds
        done.append((src, name))
        if tr.vec_targets:
            vec[src] = {'name': name, 'targets': tr.vec_targets}
        if a.list:
            print('%s -> %s: %d commands; left out %s' % (src, name, len(cmds), tr.skipped))
            print(acmd.fmt_script(cmds))
    for name in EMPTY if not a.only else ():    # --only: those scripts alone (a fighter on its base's moves keeps them)
        if name not in {n for _s, n in done}:   # a --slot-moves move (attacks4hi / lw) keeps its translation
            f.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
    f.save(a.out)
    if vec:
        print('set_vec_target_pos (carried to a point: the MSC pull, tools/vec_target.py): %s' % ', '.join(
            '%s (%d)' % (k, len(v['targets'])) for k, v in vec.items()))
    if a.vec_targets:
        json.dump(vec, open(a.vec_targets, 'w'), indent=1)
    print('%d scripts translated (%s), %d emptied' % (len(done), ', '.join(n for _s, n in done),
                                                     0 if a.only else len(EMPTY)))
    if a.others:
        os.makedirs(a.others[1], exist_ok=True)
        for fn in ('effect.bin', 'sound.bin', 'expression.bin'):
            o = acmd.ACMDFile.load(os.path.join(a.others[0], fn))
            for _s, name in done:
                if name in GAME_ONLY:
                    continue
                if fn != 'expression.bin' or acmd.crc(name) not in o.scripts:
                    o.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
            if fn == 'effect.bin' and a.effects:
                ids = {}
                for path in a.effects[0].split(','):
                    ids.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
                import ultimate_tints
                ult = os.path.basename(os.path.normpath(a.scripts))
                fx, missing = translate_effects(a.scripts, o, tr.joints, ids, skeleton_parents(a.effects[1]),
                                                locals_=skeleton_locals(a.effects[1]),
                                                tints=ultimate_tints.tints(ult) if ultimate_tints.fighter_tint(ult)
                                                else {}, baked=ultimate_tints.script_colours(a.scripts),
                                                nusktb=a.effects[1], motion_list=a.motion_list,
                                                motions=mtable_crcs(a.mtable[0]) if a.mtable else ())
                for name, cmds in fx.items():
                    o.scripts[acmd.crc(name)] = cmds
                print('%d effect scripts translated; effects without an id (left out): %s' % (
                    len(fx), ', '.join('%s x%d' % kv for kv in sorted(missing.items(), key=lambda kv: -kv[1]))))
                n = common_to_own(o, {acmd.crc(nm) for nm in fx}, ids, a.effects[0].split(',')[-1])
                print('%d Smash 4 common effects in the base\'s scripts kept -> his Ultimate ones' % n)
            smap = json.load(open(os.path.join(HERE, '..', 'reference', 'ultimate_sound_map.json')))
            if fn == 'sound.bin' and a.sound_ids:
                ids = {k: v for k, (v, _c) in smap['common_se'].items()}
                for path in a.sound_ids.split(','):
                    ids.update({k: v for k, v in json.load(open(path)).items() if not k.startswith('_')})
                st = SoundTranslator(ids, {k: v.split(',') for k, v in (x.split('=') for x in a.fail_sounds)})
                TRUE_CONDS[:] = a.cond + a.sound_cond
                sc = translate_others('sound', a.scripts, o, st,
                                      motions=mtable_crcs(a.mtable[0]) if a.mtable else ())
                TRUE_CONDS[:] = a.cond
                o.scripts.update({acmd.crc(n): c for n, c in sc.items()})
                print('%d sound scripts translated; sounds without an id (left out): %s; calls left out: %s' % (
                    len(sc), ', '.join('%s x%d' % kv for kv in sorted(st.missing.items(), key=lambda kv: -kv[1])) or '-',
                    ', '.join('%s x%d' % kv for kv in sorted(st.skipped.items(), key=lambda kv: -kv[1])) or '-'))
            if fn == 'expression.bin' and a.expressions:
                et = ExpressionTranslator(smap)
                sc = translate_others('expression', a.scripts, o, et)
                o.scripts.update({acmd.crc(n): c for n, c in sc.items()})
                print('%d expression scripts translated; rumble kinds without a match: %s; calls left out: %s' % (
                    len(sc), ', '.join('%s x%d' % kv for kv in sorted(et.missing.items(), key=lambda kv: -kv[1])) or '-',
                    ', '.join('%s x%d' % kv for kv in sorted(et.skipped.items(), key=lambda kv: -kv[1])) or '-'))
            o.save(os.path.join(a.others[1], fn))
    if a.motion_list:
        moves = motion_frames(a, done)
        if a.base_rpx:
            import kind_expand as K
            img = K.Image(a.base_rpx)
            dsrc = K.switch_targets(img, 'descriptor')[0][a.base_kind]
            g = K.branch_target(dsrc, img.w(dsrc))
            dbase = ((img.w(g) & 0xFFFF) << 16) + K.sx16(img.w(g + 4))
            table = img.w(img.w(dbase + 4))
            out = {}
            for i, (name, mv) in sorted(moves.items()):
                fl = img.w(table + 8 * i + 4)
                if bool(fl & 4) != bool(mv) or not img.w(table + 8 * i):
                    out['0x%X' % i] = {'flags': '0x%X' % ((fl & ~4) | (4 if mv else 0)), 'motion': name}
                    if not img.w(table + 8 * i):
                        out['0x%X' % i]['anim'] = '? (the base has none: its main.pac name, e.g. FitZeldaBodyMainC00Attack12)'
            print('extra_kinds.json "motions" (move flag differs from the base\'s, or a slot the base leaves empty):')
            print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
