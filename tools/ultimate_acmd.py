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
    # the dash's run transition (Ultimate's frame: 11 for the four ported so far; the base's was for its
    # own animation, Robin 17 / Zelda 16 / Pit 13 / Bowser 14, so the run cut in mid-stride; Smash 4 has
    # no TurnDash motion, its turn dash plays Dash). Game script only: the base's sound / expression
    # scripts (steps) aren't emptied for them (effects: translate_effects as before), and the dash's
    # motion_list frames aren't vl cancel frames
    'Dash': 'dash',
}
GAME_ONLY = {'dash'}
# Ultimate transition term -> Smash 4 STRANS id (vanilla dash scripts: STRANS_ON(0x1E00000A) at the run frame)
TERMS = {'FIGHTER_STATUS_TRANSITION_TERM_ID_DASH_TO_RUN': 0x1E00000A}
# --translate: script name -> motion slot for the run's extra translations
SLOTS = {}
# base scripts emptied (they'd run the base's moves on a motion we replaced without a script of ours)
EMPTY = ['attacks4hi', 'attacks4lw', 'landingairn', 'landingairf', 'landingairb', 'landingairhi']

EFFECT = {'collision_attr_normal': 0, 'collision_attr_cutup': 2, 'collision_attr_sting': 2,
          'collision_attr_elec': 3, 'collision_attr_fire': 5, 'collision_attr_purple': 0x13,
          'collision_attr_magic': 0, 'collision_attr_paralyze': 0x14, 'collision_attr_sleep': 9,
          'collision_attr_sleep_ex': 9, 'collision_attr_ice': 4,          # freezing (Lucas's PK Freeze)
          'collision_attr_cutup_metal': 2, 'collision_attr_deathball': 0}
SFX_LEVEL = {'ATTACK_SOUND_LEVEL_S': 0, 'ATTACK_SOUND_LEVEL_M': 1, 'ATTACK_SOUND_LEVEL_L': 2, 'ATTACK_SOUND_LEVEL_LL': 3}
SFX_TYPE = {'COLLISION_SOUND_ATTR_NONE': 0, 'COLLISION_SOUND_ATTR_PUNCH': 1, 'COLLISION_SOUND_ATTR_KICK': 2,
            'COLLISION_SOUND_ATTR_CUTUP': 3, 'COLLISION_SOUND_ATTR_ELEC': 7, 'COLLISION_SOUND_ATTR_FIRE': 8,
            'COLLISION_SOUND_ATTR_MAGIC': 8, 'COLLISION_SOUND_ATTR_HEAVY': 8}
REGIONS = ['NONE', 'HEAD', 'BODY', 'HIP', 'PUNCH', 'ELBOW', 'KICK', 'KNEE', 'THROW', 'OBJECT', 'SWORD', 'HAMMER',
           'BOMB', 'SPIN', 'BITE', 'MAGIC', 'PSI', 'PALUTENA', 'AURA', 'BAT', 'PARASOL', 'PIKMIN', 'WATER',
           'WHIP', 'TAIL', 'ENERGY']
REGION = {'ATTACK_REGION_' + r: i for i, r in enumerate(REGIONS)}
FACING = {'ATTACK_LR_CHECK_F': 3, 'ATTACK_LR_CHECK_B': 4, 'ATTACK_LR_CHECK_POS': 0, 'ATTACK_LR_CHECK_SPEED': 0,
          'ATTACK_LR_CHECK_LR': 3}
SETOFF = {'ATTACK_SETOFF_KIND_ON': (1, 1), 'ATTACK_SETOFF_KIND_OFF': (1, 0), 'ATTACK_SETOFF_KIND_THRU': (0, 0)}
SITUATION = {'COLLISION_SITUATION_MASK_G': 1, 'COLLISION_SITUATION_MASK_A': 2, 'COLLISION_SITUATION_MASK_GA': 3}
CATEGORY = {'COLLISION_CATEGORY_MASK_ALL': 0x3F, 'COLLISION_CATEGORY_MASK_NO_STAGE_GIMMICK': 0x1F,
            'COLLISION_CATEGORY_MASK_FIGHTER': 0x1, 'COLLISION_CATEGORY_MASK_NO_FIGHTER': 0x3E}
HIT_STATUS = {'HIT_STATUS_NORMAL': 0, 'HIT_STATUS_INVINCIBLE': 1, 'HIT_STATUS_XLU': 2, 'HIT_STATUS_OFF': 2}
ABS_KIND = {'FIGHTER_ATTACK_ABSOLUTE_KIND_THROW': 0, 'FIGHTER_ATTACK_ABSOLUTE_KIND_CATCH': 1}
CAPTURE_STATUS = {'FIGHTER_STATUS_KIND_CAPTURE_PULLED': 0x3F}
# Ultimate status flag -> Smash 4 status variable (from vanilla scripts doing the same: Cloud's jabs,
# aerials, catches; Mario's up smash for the smash hold)
FLAGS = {'FIGHTER_STATUS_ATTACK_FLAG_ENABLE_COMBO': 0x2100000D,
         'FIGHTER_STATUS_ATTACK_FLAG_ENABLE_NO_HIT_COMBO': 0x21000013,
         'FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD': 0x2100001B,
         'FIGHTER_STATUS_ATTACK_AIR_FLAG_ENABLE_LANDING': 0x2100000D,
         'FIGHTER_STATUS_CATCH_FLAG_CATCH_WAIT': 0x2100000D}
THROW_VARS = (0x11000005, 0x11000006, 0x11000007)
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


def dynamic_var(cond):
    return next((v for k, v in DYNAMIC_CONDS.items() if k in cond), None)


def words(cmds):
    return sum(len(c.encode()) // 4 for c in cmds)


def cond_true(cond):
    if cond == 'macros::is_excute(agent)' or cond in EFFECT_CONDS:
        return True
    if any(c in cond for c in TRUE_CONDS):
        return True
    if cond.startswith('!'):
        return not cond_true(cond[1:].strip())
    return False


# ---------------------------------------------------------------- translation
class Translator:
    def __init__(self, joints):
        self.joints = joints            # Ultimate bone name (lower case) -> ACMD joint ID
        self.skipped = {}
        self.frame = 0.0                # the script's frame at the current statement
        self.events = []                # (frame, call, args) of the WorkModule sets (Steve's tool requests)

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
        live = [True]              # a stack of "this block runs"
        taken = [False]
        dyn = []                   # dynamic ifs open: [where its compare goes, where its Else goes or None]
        for st in fix_split_flag_branch(fix_misplaced_else(statements(body))):
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
                        block = [cmd('Int_Var_Compare', var, 1, 0),     # method 1: !=
                                 cmd('True', 2 + words(body_t) + (2 if body_e else 0))] + body_t
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
        if name == 'AttackModule::set_add_reaction_frame':
            # frames more hitstun for hitbox ID (Magic Burst's 2, so its hits hold): that hitbox (the last
            # made with the ID, in this script so far) as its Extra_ form, HitstunMul = -frames (tools/
            # acmd_ext_cave.py: a negative one adds frames)
            return self.add_reaction(int(a[1]), float(a[2]))
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

    def attack(self, a):
        (_ag, hid, part, bone, dmg, angle, kbg, fkb, bkb, size, x, y, z, x2, y2, z2, hitlag, sdi, setoff, lr,
         set_weight, shield_dmg, trip, rehit, reflect, absorb, flinchless, no_hitlag, direct, situation, category,
         partmask, friendly, effect, lvl, attr, region) = a[:37]
        clang, rebound = SETOFF[setoff]
        if not isinstance(shield_dmg, (int, float)) or shield_dmg != shield_dmg:
            shield_dmg = 0              # f32::NAN (Kamikazee's blast): none
        common = [int(hid), int(part), self.bone(bone), float(dmg), int(angle), int(kbg), int(fkb), int(bkb), float(size),
                  float(x), float(y), float(z), EFFECT.get(effect, 0), float(trip), float(hitlag), float(sdi), clang,
                  rebound, int(round(shield_dmg)), SFX_LEVEL[lvl], SFX_TYPE.get(attr, 0), SITUATION[situation],
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
                    EFFECT.get(effect, 0), float(trip), float(hitlag), 1.0, SFX_LEVEL[lvl], SFX_TYPE.get(attr, 0),
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
}

# LAST_EFFECT_SET_* -> the Smash 4 command of the same name, its arguments scaled: Ultimate passes
# rate / alpha / colour as is (app::sv_animcmd -> EffectModule vt+0x338 / +0x348 ...: rate lands in
# the effect record +0x264, a per-set playback speed), Smash 4's alpha is a percent and its colour 0-255
LAST_EFFECT = {'LAST_EFFECT_SET_RATE': 1.0, 'LAST_EFFECT_SET_ALPHA': 100.0, 'LAST_EFFECT_SET_COLOR': 255.0}


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

    def __init__(self, joints, ids, parents, locals_=None):
        super().__init__(joints)
        self.ids, self.parents, self.locals = ids, parents, locals_ or {}
        self.missing = {}
        self.last = False
        self.turned_off = set()

    def bone(self, name):
        return self.bone_at(name, (0.0, 0.0, 0.0))[0]

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
            return [cmd(short, *[float(v) * scale for v in a[1:]])]
        if short == 'EFFECT_DETACH_KIND':
            eid = self.ids.get(a[1])
            if eid is None:
                self.missing[a[1]] = self.missing.get(a[1], 0) + 1
                return []
            return [cmd('EFFECT_DETACH_KIND', eid, int(float(a[2])) & 0xFFFFFFFF)]
        if short.endswith('_FLIP') and short[:-len('_FLIP')] in EFFECT_MACROS:
            # the macro with a mirrored twin effect (its second name) and a flip axis (last): Smash 4
            # turns effects with the facing, so the plain one (Psyche Up's aura was left out)
            short = short[:-len('_FLIP')]
            a = a[:2] + a[3:]
        if short not in EFFECT_MACROS:
            self.skip(short)
            return []
        target, shape = EFFECT_MACROS[short]
        if short.startswith('EFFECT_FLW_POS') and any(abs(float(v)) > 1e-6 for v in a[3:6]):
            # Smash 4's position-only follow adds the offset unturned to the bone's position
            # (cross_f.rpx 0x0334E4B0: effect record +0x144 bit 0x1000), Ultimate turns it with the
            # bone (down air's flash 22 along the blade sat above his head): follow fully instead
            target = 'External_Graphic' if short == 'EFFECT_FLW_POS' else 'Graphic_Effect4'
        if target == 'Graphic_Effect4' and a[1] in self.turned_off:
            # a NO_STOP effect its own script turns off: the plain follow (killed with the motion
            # too), or a script cut before the EFFECT_OFF_KIND (forward air landing early) leaves an
            # endless emitter on for good (Graphic_Effect4: EffectModule 0x271A, no 0x8000 flag)
            target = 'External_Graphic'
        eid = self.ids.get(a[1])
        self.last = eid is not None
        if eid is None:
            if a[1] != 'null':
                self.missing[a[1]] = self.missing.get(a[1], 0) + 1
            return []
        bone, *place = self.place(a[2], a[3:6], a[6:9])
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


def translate_effects(scripts_dir, effect_bin, joints, ids, parents, skip=('special', 'final'), locals_=None):
    """every effect_* function of the dump -> the effect script of the same Smash 4 name (TRANSLATE's
    for the translated moves), replacing the base's (its own effects, e.g. Zelda's sparkles); not the
    moves still the base's (specials, Final Smash). Returns {Smash 4 name: commands}, {missing name:
    count}"""
    global EFFECT_CONDS
    # the facing-left branch: in the dumps the facing-right one is often nested inside it (a misplaced
    # else), so it's the one that always holds the effect; Smash 4 places effects by the bones anyway
    EFFECT_CONDS = (LR_LEFT,)
    tr = EffectTranslator(joints, ids, parents, locals_)
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
            if name not in TRANSLATE.values() and (name.startswith(skip) or acmd.crc(name) not in effect_bin.scripts):
                continue
            tr.last = False
            tr.turned_off = set(re.findall(r'EFFECT_OFF_KIND\(agent, Hash40::new\("([^"]+)"', body))
            cmds = tr.script(body)
            # looping motions: the base's script ends Loop_Rest, JUMP(itself); Ultimate re-runs its own
            base = [c.name for c in effect_bin.scripts.get(acmd.crc(name), [])]
            if 'Loop_Rest' in base:
                cmds = cmds[:-1] + [cmd('Loop_Rest'), cmd('JUMP', acmd.crc(name)), acmd.Command(acmd.END)]
            out[name] = cmds
    EFFECT_CONDS = ()
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

    def sid(self, name):
        v = self.ids.get(name.lower()) if isinstance(name, str) else None
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
        status = k[0] == 'RUMBLE_STATUS'
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


def translate_others(kind, scripts_dir, base_bin, tr, skip=('special', 'final')):
    """every sound_* / expression_* function (kind) of the dump -> the script of the same Smash 4 name, as
    translate_effects; a looping one (wait_loop_sync_mot) ends Loop_Rest, JUMP(itself) as vanilla's do"""
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
            if name not in TRANSLATE.values() and (name.startswith(skip) or acmd.crc(name) not in base_bin.scripts):
                continue
            tr.loop = False
            tr.has_rumble = 'set_rumble' in body
            tr.drop = set(n for k, v in getattr(tr, 'fail', {}).items() if k in body for n in v)
            cmds = tr.script(first_voice_region(body) if kind == 'sound' else body)
            if tr.loop:
                cmds = cmds[:-1] + [cmd('Loop_Rest'), cmd('JUMP', acmd.crc(name)), acmd.Command(acmd.END)]
            out[name] = cmds
    return out


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
    n1, _n2 = struct.unpack('>HH', d[:4])
    table0 = struct.unpack('>%dh' % n1, d[4:4 + 2 * n1])
    s4_to_ult = {s: u for s, u in U.STANDARD}
    out = {}
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
    import ultimate_vl_blend
    ultimate_vl_blend.apply_blends(vf, ml)      # Ultimate's blend into each common motion (byte 1)
    open(args.mtable[1], 'wb').write(struct.pack('>%dI' % len(mt), *mt))
    open(args.vl[1], 'wb').write(vf.build())
    return moves


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
    ap.add_argument('--cond', action='append', default=[], help='a condition taken as true (substring of the '
                    'dump\'s condition, e.g. MATERIAL_KIND_IRON) for Steve\'s tool material); repeatable')
    ap.add_argument('--dyn-cond', action='append', default=[], metavar='SUBSTRING=VAR',
                    help="a condition decided in game: the if / else kept as Int_Var_Compare(VAR != 0) True / Else "
                         "(e.g. FLAG_CRITICAL_HIT=0x1000009A, Hero's critical hit); repeatable")
    a = ap.parse_args()
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
    for src, name in TRANSLATE.items():
        if a.only and src not in a.only:
            continue
        path = os.path.join(a.scripts, src + '.txt')
        body = None
        if os.path.exists(path):
            body = functions(open(path).read()).get('game_' + src.lower())
        if body is None and name not in SLOTS:
            continue
        tr.skipped = {}
        # a slot of ours with no game script in the dump (SpecialNCancel): empty scripts, so the
        # slot's base move (a custom-move variant) doesn't run on it
        cmds = tr.script(body) if body is not None else [acmd.Command(acmd.END)]
        f.scripts[acmd.crc(name)] = cmds
        done.append((src, name))
        if a.list:
            print('%s -> %s: %d commands; left out %s' % (src, name, len(cmds), tr.skipped))
            print(acmd.fmt_script(cmds))
    for name in EMPTY if not a.only else ():    # --only: those scripts alone (a fighter on its base's moves keeps them)
        f.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
    f.save(a.out)
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
                fx, missing = translate_effects(a.scripts, o, tr.joints, ids, skeleton_parents(a.effects[1]),
                                                locals_=skeleton_locals(a.effects[1]))
                for name, cmds in fx.items():
                    o.scripts[acmd.crc(name)] = cmds
                print('%d effect scripts translated; effects without an id (left out): %s' % (
                    len(fx), ', '.join('%s x%d' % kv for kv in sorted(missing.items(), key=lambda kv: -kv[1]))))
            smap = json.load(open(os.path.join(HERE, '..', 'reference', 'ultimate_sound_map.json')))
            if fn == 'sound.bin' and a.sound_ids:
                ids = {k: v for k, (v, _c) in smap['common_se'].items()}
                for path in a.sound_ids.split(','):
                    ids.update({k: v for k, v in json.load(open(path)).items() if not k.startswith('_')})
                st = SoundTranslator(ids, {k: v.split(',') for k, v in (x.split('=') for x in a.fail_sounds)})
                sc = translate_others('sound', a.scripts, o, st)
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
