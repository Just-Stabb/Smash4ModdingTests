#!/usr/bin/env python3
"""Ultimate ACMD (game scripts, as decompiled to smashline Rust: WuBoytH/SSBU-Dumped-Scripts,
smashline/lua2cpp_<fighter>/<fighter>/<Motion>.txt) -> Smash 4 game.bin scripts
(docs/ultimate-fighter-port.md, "Moves").

  python3 tools/ultimate_acmd.py SCRIPT_DIR GAME_BIN OUT_GAME_BIN MODEL_DIR [--only NAME...] [--list]
      [--others IN_DIR OUT_DIR] [--motion-list MOTION_LIST --mtable IN OUT --vl IN OUT]

MODEL_DIR: the fighter's converted model/body/c00 (model.vbn + model.jtb: Ultimate bone names ->
ACMD joint IDs). Every script in TRANSLATE is converted and replaces the base's script of the same
Smash 4 name; the rest of GAME_BIN stays.

What maps to what:
- frame(n) / wait(n) -> FRAME / WAIT; FT_MOTION_RATE(r) -> Set_Frame_Duration(r)
- ATTACK -> Special_Hitbox for a sphere, Extended_Special_Hitbox for a capsule (never with its end at its
  start: in game that hit the whole stage), with the value tables below
  (effect, sound, region, facing, clank, situation, categories; taken from vanilla scripts:
  Cloud / Marth / Ike / Ganondorf / Pikachu); set_weight -> Set_Weight_Hitbox
- AttackModule::clear_all / clear(id) -> Remove_All_Hitboxes / Remove_Hitbox
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
motions). Landing motions are left as they are (their lag is fighter_param's). With --base-rpx /
--base-kind, prints the motions whose Ultimate "move" flag (0x4, the root moves the fighter; the
same bit as the low byte of a Smash 4 motion table entry's flags) differs from the base's, and
the slots the base leaves empty, as the "motions" of the kind's extra_kinds.json record
(tools/kind_expand.py).
"""
import argparse
import json
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
}
# base scripts emptied (they'd run the base's moves on a motion we replaced without a script of ours)
EMPTY = ['attacks4hi', 'attacks4lw', 'landingairn', 'landingairf', 'landingairb', 'landingairhi']

EFFECT = {'collision_attr_normal': 0, 'collision_attr_cutup': 2, 'collision_attr_sting': 2,
          'collision_attr_elec': 3, 'collision_attr_fire': 5, 'collision_attr_purple': 0x13,
          'collision_attr_magic': 0, 'collision_attr_paralyze': 0x14, 'collision_attr_sleep': 9}
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
                if cond.startswith('if '):
                    out.append(('elseif', cond[3:].strip()))
                else:
                    out.append(('else',))
                i = k + 1
            else:
                out.append(('end',))
                i += 1
            continue
        if body.startswith('if ', i):
            k = i + 3
            depth = 0
            while not (body[k] == '{' and depth == 0):
                depth += {'(': 1, ')': -1}.get(body[k], 0)
                k += 1
            out.append(('if', body[i + 3:k].strip()))
            i = k + 1
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


LR_LEFT = 'get_value_float(agent.lua_state_agent, *SO_VAR_FLOAT_LR) < 0.0'
EFFECT_CONDS = ()


def cond_true(cond):
    if cond == 'macros::is_excute(agent)' or cond in EFFECT_CONDS:
        return True
    if cond.startswith('!'):
        return not cond_true(cond[1:].strip())
    return False


# ---------------------------------------------------------------- translation
class Translator:
    def __init__(self, joints):
        self.joints = joints            # Ultimate bone name (lower case) -> ACMD joint ID
        self.skipped = {}

    def bone(self, name):
        if name == 'top':
            return 0
        if name not in self.joints:
            raise KeyError('bone %r has no joint ID' % name)
        return self.joints[name]

    def skip(self, what):
        self.skipped[what] = self.skipped.get(what, 0) + 1

    def script(self, body):
        cmds = []
        live = [True]              # a stack of "this block runs"
        taken = [False]
        for st in statements(body):
            kind = st[0]
            if kind == 'if':
                c = live[-1] and cond_true(st[1])
                live.append(c)
                taken.append(c)
                continue
            if kind == 'elseif':
                c = live[-2] and not taken[-1] and cond_true(st[1])
                live[-1] = c
                taken[-1] = taken[-1] or c
                continue
            if kind == 'else':
                live[-1] = live[-2] and not taken[-1]
                taken[-1] = True
                continue
            if kind == 'end':
                if len(live) > 1:
                    live.pop()
                    taken.pop()
                continue
            if not live[-1]:
                continue
            if kind == 'other':
                self.skip(st[1].split('(')[0][:40])
                continue
            cmds += self.call(st[1], [value(a) for a in st[2]], st[2])
        return cmds + [acmd.Command(acmd.END)]

    def call(self, name, a, raw):
        short = name.split('::')[-1]
        if short == 'frame':
            return [cmd('FRAME', int(round(a[1])))]
        if short == 'wait':
            return [cmd('WAIT', int(round(a[1])))]
        if short == 'FT_MOTION_RATE':
            return [cmd('Set_Frame_Duration', float(a[1]))]
        if short == 'ATTACK':
            return self.attack(a)
        if name == 'AttackModule::clear_all':
            return [cmd('Remove_All_Hitboxes')]
        if name == 'AttackModule::clear':
            return [cmd('Remove_Hitbox', int(a[1]))]
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


class EffectTranslator(Translator):
    """effect_* functions -> Smash 4 effect scripts. ids: Ultimate effect name -> Smash 4 effect id
    (the common bank's for sys_*; a fighter bank's once converted); other names are left out and
    counted. Bones without a joint id use their nearest ancestor that has one (parents: Ultimate's
    skeleton, lower-case names)."""

    def __init__(self, joints, ids, parents):
        super().__init__(joints)
        self.ids, self.parents = ids, parents
        self.missing = {}

    def bone(self, name):
        n = name.lower()
        while n not in self.joints and n != 'top' and n in self.parents:
            n = self.parents[n]
        return super().bone(n)

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
        if short not in EFFECT_MACROS:
            self.skip(short)
            return []
        target, shape = EFFECT_MACROS[short]
        eid = self.ids.get(a[1])
        if eid is None:
            if a[1] != 'null':
                self.missing[a[1]] = self.missing.get(a[1], 0) + 1
            return []
        place = [float(v) for v in a[3:10]]                      # x, y, z, rx, ry, rz, size
        if shape.startswith('full'):
            rest = [float(v) for v in a[10:16]] + [int(bool(a[16]))]
            extra = a[17:]
        else:
            rest = [int(bool(a[10]))]
            extra = a[11:]
        if shape.endswith('+alpha'):
            rest.append(float(extra[0]) * 100.0)
        elif shape.endswith('+color'):
            rest += [min(255.0, float(v) * 255.0) for v in extra[:3]]
        return [cmd(target, eid, self.bone(a[2]), *place, *rest)]


def translate_effects(scripts_dir, effect_bin, joints, ids, parents, skip=('special', 'final')):
    """every effect_* function of the dump -> the effect script of the same Smash 4 name (TRANSLATE's
    for the translated moves), replacing the base's (its own effects, e.g. Zelda's sparkles); not the
    moves still the base's (specials, Final Smash). Returns {Smash 4 name: commands}, {missing name:
    count}"""
    global EFFECT_CONDS
    # the facing-left branch: in the dumps the facing-right one is often nested inside it (a misplaced
    # else), so it's the one that always holds the effect; Smash 4 places effects by the bones anyway
    EFFECT_CONDS = (LR_LEFT,)
    tr = EffectTranslator(joints, ids, parents)
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
            if name.startswith(skip) or acmd.crc(name) not in effect_bin.scripts and name not in TRANSLATE.values():
                continue
            cmds = tr.script(body)
            # looping motions: the base's script ends Loop_Rest, JUMP(itself); Ultimate re-runs its own
            base = [c.name for c in effect_bin.scripts.get(acmd.crc(name), [])]
            if 'Loop_Rest' in base:
                cmds = cmds[:-1] + [cmd('Loop_Rest'), cmd('JUMP', acmd.crc(name)), acmd.Command(acmd.END)]
            out[name] = cmds
    EFFECT_CONDS = ()
    return out, tr.missing


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
        if name.startswith('landing'):          # landing lag: fighter_param's landing frames
            continue
        h = acmd.crc(name)
        if h in mt:
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
        xs, xe, cancel = ent[0]['extra'][:3]
        for k, v in ((2, cancel), (3, xs), (4, xe)):
            byte(i, k, v)
        moves[i] = (name, ent[0]['flags'] & 4)
        print('  0x%03X %-16s cancel %2d, intangible %d-%d, move %d' % (i, name, cancel, xs, xe, bool(ent[0]['flags'] & 4)))
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
                         'Smash 4 id, e.g. reference/ultimate_sys_effects.json; NUSKTB: Ultimate skeleton)')
    a = ap.parse_args()
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
        if not os.path.exists(path):
            continue
        fns = functions(open(path).read())
        body = fns.get('game_' + src.lower())
        if body is None:
            continue
        tr.skipped = {}
        cmds = tr.script(body)
        f.scripts[acmd.crc(name)] = cmds
        done.append((src, name))
        if a.list:
            print('%s -> %s: %d commands; left out %s' % (src, name, len(cmds), tr.skipped))
            print(acmd.fmt_script(cmds))
    for name in EMPTY:
        f.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
    f.save(a.out)
    print('%d scripts translated (%s), %d emptied' % (len(done), ', '.join(n for _s, n in done), len(EMPTY)))
    if a.others:
        os.makedirs(a.others[1], exist_ok=True)
        for fn in ('effect.bin', 'sound.bin', 'expression.bin'):
            o = acmd.ACMDFile.load(os.path.join(a.others[0], fn))
            for _s, name in done:
                if fn != 'expression.bin' or acmd.crc(name) not in o.scripts:
                    o.scripts[acmd.crc(name)] = [acmd.Command(acmd.END)]
            if fn == 'effect.bin' and a.effects:
                ids = {}
                for path in a.effects[0].split(','):
                    ids.update({k: int(v, 0) for k, v in json.load(open(path)).items() if not k.startswith('_')})
                fx, missing = translate_effects(a.scripts, o, tr.joints, ids, skeleton_parents(a.effects[1]))
                for name, cmds in fx.items():
                    o.scripts[acmd.crc(name)] = cmds
                print('%d effect scripts translated; effects without an id (left out): %s' % (
                    len(fx), ', '.join('%s x%d' % kv for kv in sorted(missing.items(), key=lambda kv: -kv[1]))))
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
