#!/usr/bin/env python3
"""Greninja's clones / smash charges mod (fighters/gekkouga/README.md "Clones v1"): builds every file of it.

  python3 tools/gekkouga_build.py msc VANILLA.c OUT.c          the MSC source: universal mechanics + this mod
  python3 tools/gekkouga_build.py acmd USER_ANIMCMD_DIR OUT_DIR the body scripts (smash growth) + the clone's
  python3 tools/gekkouga_build.py data VANILLA_FIGHTER_DIR OUT  the clone's model (c00-c07) / motion folders
  python3 tools/gekkouga_build.py all VANILLA_ROOT USER_ROOT OUT (VANILLA_ROOT/fighter/gekkouga, USER_ROOT/fighter/
                                                                gekkouga/script/animcmd) -> OUT/fighter/gekkouga/...
  python3 tools/gekkouga_build.py skeleton PACMAN_FIGHTER_DIR OUT_FIGHTER [TEST_ONLY_DIR]   skeleton v1: its files
                                                                (vanilla fighter/pacman: its hydrant's model / motion)
  python3 tools/gekkouga_build.py trail PACMAN_FIGHTER_DIR OUT_FIGHTER      burn v2: the fire trail's files
  python3 tools/gekkouga_build.py effects VANILLA_EFFECT_DIR KIRBY_PTCL FX_PKG OUT_FIGHTER   skeleton v1.2 on: his
                                                                effect bank + the flipbooks (tools/gekkouga_fx.py) ->
                                                                OUT_FIGHTER/effect/gekkouga/gekkouga.010d0000.ptcl / .efc
                                                                [--common=COMMON_PTCL: ice detonation v1's sparkles,
                                                                the common bank's emitter; FX_PKG with ice_boom_15]

VANILLA.c: the decompiled vanilla MSC with its labels (git show 0932c7b:fighters/gekkouga/gekkouga.c); the result is
fighters/gekkouga/gekkouga.c. The MSC step runs tools/universal_mechanics.py on it (roll-off 2.2 / 1.0, Hero's
momentum, reverse tilts, tilts / down smash / shield out of run: the user's rolloff_hero_v1 gekkouga.mscsb compiles
to the same functions, msc_fingerprint 0 differ), then patches the sites below and appends fighters/gekkouga/clones.c.
The clone article's MSC is fighters/gekkouga/weapons/clone.c (compiled as it is).
"""
import math
import os
import re
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CLONES_C = os.path.join(ROOT, 'fighters', 'gekkouga', 'clones.c')
CLONE_MSC = os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'clone.c')
SHURIKEN_MSC = os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'shuriken.c')   # clone articles v1

# ---------------------------------------------------------------- MSC
# (function, old text, new text): each old text must be in that function exactly once
MSC_EDITS = [
    ('func_82', 'rolloff_hold_update(); // roll-off: the air speed cap off while the stick holds the way he moves (universal mechanics)\n',
     'rolloff_hold_update(); // roll-off: the air speed cap off while the stick holds the way he moves (universal mechanics)\n'
     '    gekkouga_frame(); // Greninja mod: the down special charge / clones / burnout, smash chains (clones.c)\n'),
    # the down special inputs: the stance, the ability, or nothing (gk_lw_press)
    ('func_43', 'func_16(0x155, 0x1);\n                return 0x1;',
     'if (gk_lw_press()) // Greninja mod: charge stance / ability (clones.c)\n                {\n'
     '                    return 0x1;\n                }'),
    ('func_58', 'func_16(0x155, 0x1);\n                return 0x1;',
     'if (gk_lw_press()) // Greninja mod: charge stance / ability (clones.c)\n                {\n'
     '                    return 0x1;\n                }'),
    ('func_675', 'func_16(0x155, 0x1);\n                    return 0x1;',
     'if (gk_lw_press()) // Greninja mod: charge stance / ability (clones.c)\n                    {\n'
     '                        return 0x1;\n                    }'),
    ('func_1999', 'func_16(0x155, 0x1);\n                    return;',
     'if (gk_lw_press()) // Greninja mod: charge stance / ability (clones.c)\n                    {\n'
     '                        return;\n                    }'),
    # skeleton v1.6: no side special while a skeleton of his runs (its input: the hold's start, func_2379)
    ('func_2379', '        if (global24 & 0x2000)\n        {\n            WorkModule(0x2710, 0x2000007c);',
     '        if (global24 & 0x2000 && gk_ss_allowed()) // Greninja mod: not while a skeleton runs (clones.c)\n'
     '        {\n            WorkModule(0x2710, 0x2000007c);'),
    # tilt chain v1: the jab's / tilts' starts (their status mains, before the loop is set)
    ('func_263', '    func_78(func_270);', '    gk_tc_start(0x4); // Greninja mod: tilt chain (clones.c)\n    func_78(func_270);'),
    ('func_275', '    func_78(func_277);', '    gk_tc_start(0x1); // Greninja mod: tilt chain (clones.c)\n    func_78(func_277);'),
    ('func_278', '    func_78(func_279);', '    gk_tc_start(0x2); // Greninja mod: tilt chain (clones.c)\n    func_78(func_279);'),
    ('func_281', '    func_78(func_282);', '    gk_tc_start(0x3); // Greninja mod: tilt chain (clones.c)\n    func_78(func_282);'),
    # SpecialLw 0x155: the charge stance (no counter)
    ('func_2336', '    func_78(func_2337);', '    gk_lw_main(); // Greninja mod: the charge (clones.c)\n    func_78(gk_lw_loop);'),
    ('func_2338', '    VisibilityModule(0x2710, 0x1);',
     '    VisibilityModule(0x2710, 0x1);\n    EffectModule(0x2723, 0x1000047, 0x1, 0x1); // Greninja mod: the charge bar off'),
    # smash starts: auto release (a full stored charge / a chain), no attack when released early
    ('func_286', '    func_78(func_287);', '    gk_sm_start_main(0x1); // Greninja mod (clones.c)\n    func_78(func_287);'),
    ('func_295', '    func_294(0x63);', '    gk_sm_start_main(0x2); // Greninja mod (clones.c)\n    func_294(0x63);'),
    ('func_303', '    func_78(func_304);', '    gk_sm_start_main(0x4); // Greninja mod (clones.c)\n    func_78(func_304);'),
    # smash holds: the kept charge
    ('func_288', '        func_283();\n    }\n    global16 = func_283;',
     '        gk_sm_hold_tick();\n    }\n    global16 = gk_sm_hold_tick; // Greninja mod: the kept charge (clones.c)'),
    ('func_297', '        func_283();\n    }\n    global16 = func_283;',
     '        gk_sm_hold_tick();\n    }\n    global16 = gk_sm_hold_tick; // Greninja mod: the kept charge (clones.c)'),
    ('func_305', '        func_283();\n    }\n    global16 = func_283;',
     '        gk_sm_hold_tick();\n    }\n    global16 = gk_sm_hold_tick; // Greninja mod: the kept charge (clones.c)'),
    # aerial chain v1: the aerial status (AttackAir 0x34): its start notes the aerial (after func_314 picks its motion),
    # its loop tries a chain cancel first (after func_56's own interrupts)
    ('func_2382', '    func_314();\n', '    func_314();\n    gk_ac_start(); // Greninja mod: aerial chains (clones.c)\n'),
    # clone articles v1: his shot's shuriken copies (one per clone out) right after his own shot
    ('func_2271', '        ArticleModule(0x2719, 0);\n', '        ArticleModule(0x2719, 0);\n        gk_sh_copies(); // Greninja mod: clone articles (clones.c)\n'),
    ('func_2279', '        ArticleModule(0x2719, 0);\n', '        ArticleModule(0x2719, 0);\n        gk_sh_copies(); // Greninja mod: clone articles (clones.c)\n'),
    ('func_2383', '    if (func_56())\n    {\n        return 0x1;\n    }\n',
     '    if (func_56())\n    {\n        return 0x1;\n    }\n    if (gk_ac_try()) // Greninja mod: aerial chains (clones.c)\n'
     '    {\n        return 0x1;\n    }\n'),
]
# whole loop bodies replaced: (function, new body)
MSC_BODIES = {
    'func_287': ('int', 'return gk_sm_start_loop(0x1); // Greninja mod (clones.c)'),
    'func_296': ('int', 'return gk_sm_start_loop(0x2); // Greninja mod (clones.c)'),
    'func_304': ('int', 'return gk_sm_start_loop(0x4); // Greninja mod (clones.c)'),
    'func_289': ('int', 'return gk_sm_hold_loop(0x1); // Greninja mod (clones.c)'),
    'func_299': ('int', 'return gk_sm_hold_loop(0x2); // Greninja mod (clones.c)'),
    'func_306': ('int', 'return gk_sm_hold_loop(0x4); // Greninja mod (clones.c)'),
    # skeleton v1: Shadow Sneak's per-frame: no vanish / teleport, the Running Skeleton at the shadow (clones.c)
    'func_2291': ('void', 'gk_ss_tick(); // Greninja mod: skeleton v1 (clones.c)'),
    # aligned kick v1: SpecialLwAttack 0x161 (unused since clones v1: no counter) is the aligned kick (clones.c gk_ak_*)
    'func_2351': ('int', 'return gk_ak_pre(); // Greninja mod: aligned kick v1 (clones.c)'),
    'func_2352': ('void', 'gk_ak_main(); // Greninja mod: aligned kick v1 (clones.c)'),
    'func_2358': ('void', 'gk_ak_init(); // Greninja mod: aligned kick v1 (clones.c)'),
    'func_2359': ('void', 'gk_ak_exec(); // Greninja mod: aligned kick v1 (clones.c)'),
    'func_2355': ('void', 'gk_ak_end(); // Greninja mod: aligned kick v1 (clones.c)'),
    # ... and SpecialLwHit 0x160 (unused) the split clones' regroup call: the start of his stance (clones.c gk_rg_*)
    'func_2346': ('void', 'gk_rg_main(); // Greninja mod: aligned kick v1, the regroup (clones.c)'),
    'func_2347': ('int', 'return gk_rg_loop(); // Greninja mod: aligned kick v1, the regroup (clones.c)'),
    'func_2349': ('void', 'func_2340(); // Greninja mod: the regroup: the stance\'s physics (clones.c)'),
}
# attack loops: a chain cancel first
MSC_CHAIN = {'func_293': 0x1, 'func_302': 0x2, 'func_309': 0x4}
# tilt chain v1: the jab's / tilts' loops (Attack 0x25, AttackS3 0x28, AttackHi3 0x29, AttackLw3 0x2A): a tilt chain first
MSC_TILT_CHAIN = ('func_270', 'func_277', 'func_279', 'func_282')


def func_span(src, name):
    m = re.search(r'^(?:int|void|float)\s+%s\s*\([^)]*\)\s*\{' % re.escape(name), src, re.M)
    assert m, 'no function %s' % name
    i, d = m.end(), 1
    while d:
        d += (src[i] == '{') - (src[i] == '}')
        i += 1
    return m.start(), m.end(), i


def patch_msc(src):
    for fn, old, new in MSC_EDITS:
        a, b, c = func_span(src, fn)
        body = src[b:c]
        assert body.count(old) == 1, '%s: %r found %d times' % (fn, old, body.count(old))
        src = src[:b] + body.replace(old, new) + src[c:]
    for fn, (typ, body) in MSC_BODIES.items():
        a, b, c = func_span(src, fn)
        src = src[:a] + '%s %s()\n{\n    %s\n}' % (typ, fn, body) + src[c:]
    for fn, t in MSC_CHAIN.items():
        a, b, c = func_span(src, fn)
        ret = 'return 0x1;' if src[a:b].startswith('int') else 'return;'
        src = src[:b] + '\n    if (gk_chain_try(0x%X)) // Greninja mod: smash chains (clones.c)\n    {\n        %s\n    }' % (
            t, ret) + src[b:]
    for fn in MSC_TILT_CHAIN:
        a, b, c = func_span(src, fn)
        ret = 'return 0x1;' if src[a:b].startswith('int') else 'return;'
        decl = re.match(r'\n(    (?:int|float) \w+;\n)*', src[b:])
        at = b + decl.end()
        src = src[:at] + '    if (gk_tc_try()) // Greninja mod: tilt chain (clones.c)\n    {\n        %s\n    }\n' % ret + src[at:]
    return src + '\n' + open(CLONES_C).read()


ROLLOFF_SPEED = 2.5               # skeleton v1.3 package (the user: "Greninja's roll doesn't move him anywhere, please give
ROLLOFF_AIR_MULT = 1.24           # him a 2.5 roll speed with a 1.24 roll speed multiplier"): his rolls had no roll-off
                                  # speed (his game.bin never got tools/rolloff_acmd.py; the MSC's rolls are kinetic type
                                  # 0x6, which moves only by that speed: they stood still); the roll-off air multiplier,
                                  # and his ground cap lifted (universal_mechanics.py --ground-uncapped, the user: "uncap
                                  # his roll speed")
ROLLOFF_SCRIPTS = ('EscapeF', 'EscapeB')


def cmd_msc(vanilla, out):
    tmp = out + '.um.c'
    subprocess.run([sys.executable, os.path.join(HERE, 'universal_mechanics.py'), '--name', 'gekkouga', '--air-mult',
                    str(ROLLOFF_AIR_MULT), '--ground-uncapped', vanilla, tmp], check=True, stdout=subprocess.DEVNULL)
    src = open(tmp).read()
    os.remove(tmp)
    open(out, 'w').write(patch_msc(src))


def compile_msc(src, out):
    subprocess.run([sys.executable, os.path.join(HERE, 'msclang', 'msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'),
                    src, '-o', out], check=True)



# ---------------------------------------------------------------- ACMD
SMASH_SCRIPTS = ('attacks4', 'attacks4hi', 'attacks4lw', 'attackhi4', 'attacklw4')
GROW = 5.0                 # v4 (the user): the hitboxes grow with the effects: every smash is a full charge, x5 (v1-v3 1.5)
SWORD_BONES = (24, 25)     # v4: his water sword's bones: a hitbox on them also has its offset x5 (the sword effect and its
                           # trail grow from the bone, so the hitboxes stay along the 5x sword); others (body bones) keep it
EFFECT_GROW = 5.0          # v3 (the user): its effects x5 (clones.c gk_smash_fx_max()); its trails' (Sword_Glow) points too
HOLD_SCRIPTS = ('attacks4hold', 'attackhi4hold', 'attacklw4hold')   # v3: their effects at size 0 (his MSC draws them, gk_sm_fx)
HOLD_EFFECTS = ('External_Graphic', 'Graphic_Effect', 'Graphic_Effect2')
CHARGE_DAMAGE = 1.0        # the clones' copies of his smash hitboxes: x this damage. Clones v1 - nair / fair v1: 1.4 (Smash
                           # 4's full charge, the attack's 0x1000000 ratio 1.0, which an article's attack doesn't get);
                           # smash tune v1 (the user: "make all of the smash attacks do the same damage as if they were
                           # uncharged"): 1.0, as his own (clones.c gk_sm_ratio 0)
HITBOXES = ('Hitbox', 'Special_Hitbox', 'Extended_Hitbox', 'Extended_Special_Hitbox')
CLONE_GAME = set(HITBOXES) | {'FRAME', 'WAIT', 'Remove_All_Hitboxes', 'Remove_Hitbox', 'Move_Hitbox', 'Script_End'}
CLONE_EFFECT = {'FRAME', 'WAIT', 'Script_End', 'Graphic_Effect2', 'External_Graphic', 'EFFECT_FLIP', 'EFFECT_FOLLOW_FLIP',
                'Terminate_Graphic_Effect', 'Sword_Glow', 'Terminate_Sword_Glow',
                # clone fixes v1 (the user: "Up air's twist doesn't appear", "grab's effect doesn't appear"): every effect
                # request his scripts use (up air's twist is Graphic_Effect5), their rate / colour
                'Graphic_Effect', 'Graphic_Effect3', 'Graphic_Effect4', 'Graphic_Effect5', 'External_Graphic_Effect2',
                'LANDING_EFFECT_FLIP', 'EFFECT_COLOR', 'LAST_EFFECT_SET_RATE'}
CLONE_EFFECT_SKIP = {'CALL', 'JUMP', 'Set_Loop', 'Goto', 'Loop_Rest', 'WAIT_LOOP_CLR'}   # clone fixes v1: a motion's
                                           # effect script copied (its conditions' True branches: flatten) unless it
                                           # calls / jumps / loops
FLOW = {'Set_Loop', 'Goto', 'Float_Var_Compare', 'True', 'Else', 'False', 'IS_FLAG', 'CALL', 'JUMP', 'EXECUTE',
        'Loop_Rest', 'Float_Compare', 'WAIT_LOOP_CLR'}
NO_CLONE = {'IS_FLAG', 'CALL', 'JUMP'}     # scripts using these (his counter's attacks, ...) aren't copied
FLOW_KEEP_SAFE = {'SET_FLOAT'}             # kept inside a loop / condition (position variables only: from an article
                                           # they find nobody), never anything else
FINAL_FIRST = 0x295                        # his Final Smash's motions (0x295 - 0x29B): not copied (the clones idle then)
WEAPON_JOINT = 0x7D0                       # an article's joint = 0x7D0 + its model.jtb table-0 entry


def param(c, name):
    return c.info['syntax'].index(name)


CLONE_JOINT_FIX = {25: 'RHaveN'}   # clone fixes v2: his joint 25 is model.jtb table 0's ThrowN, which no motion moves (his
                                   # sword / shuriken / smash swords follow it, and sweep on him: something native moves it);
                                   # on the clones his right hand. Skeleton v1.4 shipped the left hand with TEST_ONLY_DATA
                                   # clone_sword_rhave / clone_sword_thrown; confirmed in game (the user: "HaveR fixed the
                                   # sword"): the right hand, released in skeleton v1.5


def bone_map(jtb_bytes, vbn_path, fix=None):
    """his body joint id (table 0 below 1000, table 1 from 1000) -> the clone article's (0x7D0 + table-0 entry):
    a bone missing from table 0 goes to its nearest ancestor that is there; fix: {joint: bone name} taken instead
    (CLONE_JOINT_FIX)"""
    import port_check
    import omo
    t0, t1 = port_check.jtb(jtb_bytes)
    bones = omo.vbn_read(vbn_path)
    where = {b: n for n, b in enumerate(t0)}
    names = [n for n, _p, _h in bones]
    fix = CLONE_JOINT_FIX if fix is None else fix

    def m(j):
        if j == 0:
            return 0
        if j in fix:
            return WEAPON_JOINT + where[names.index(fix[j])]
        b = t0[j] if j < 1000 else t1[j - 1000]
        while b not in where:
            b = bones[b][1]
            assert 0 <= b < len(bones), 'joint %d: no ancestor in table 0' % j
        return WEAPON_JOINT + where[b]
    return m


def spans(cmds):
    """indices inside a control-flow span (a Set_Loop .. Goto, a condition .. its block's end): kept as they are"""
    inside = set()
    for i, c in enumerate(cmds):
        if c.name in ('Set_Loop',):
            inside.add(i)
            for j in range(i + 1, len(cmds)):
                inside.add(j)
                if cmds[j].name == 'Goto':
                    break
        if c.name in ('Float_Var_Compare', 'Float_Compare', 'IS_FLAG'):
            # the condition and its True / Else blocks up to the next FRAME / WAIT at depth 0 (vanilla shapes only)
            inside.add(i)
            for j in range(i + 1, len(cmds)):
                inside.add(j)
                if cmds[j].name in ('FRAME', 'Remove_All_Hitboxes') and j > i + 2:
                    break
    return inside


SMASH_STAR = 0x100000F           # tuning v1 (the user: "please make the smash attack charging star effect normal sized"):
                                  # the smashes' charge-start star flash (their frame 4 / 6) stays at its size (v3 - clone
                                  # moves v1: x EFFECT_GROW, a screen-wide burst); the release effects and the sword grow


def scale_smash(game, effect):
    """his smash scripts: hitbox sizes x GROW (game), effect sizes x EFFECT_GROW (effect; a trail's two points too:
    its length); v3: the hold scripts' effects at size 0 (his MSC draws them by the charge)"""
    n = 0
    for name in SMASH_SCRIPTS:
        for f in (game, effect):
            s = f.script(name)
            if not s:
                continue
            for c in s:
                syn = c.info['syntax']
                if 'Size' in syn and (c.name in HITBOXES or f is effect) and not \
                        (f is effect and int(c.params[0]) == SMASH_STAR):
                    k = syn.index('Size')
                    c.params[k] = round(float(c.params[k]) * (GROW if f is game else EFFECT_GROW), 4)
                    n += 1
                if f is game and c.name in HITBOXES and int(c.params[syn.index('Bone')]) in SWORD_BONES:
                    for nm in ('X', 'Y', 'Z', 'X2', 'Y2', 'Z2'):
                        if nm in syn:
                            k = syn.index(nm)
                            c.params[k] = round(float(c.params[k]) * GROW, 4)
                if f is effect and c.name == 'Sword_Glow':
                    for nm in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'):
                        k = syn.index(nm)
                        c.params[k] = round(float(c.params[k]) * EFFECT_GROW, 6)
    for name in HOLD_SCRIPTS:
        s = effect.script(name)
        for c in s or []:
            if c.name in HOLD_EFFECTS:
                c.params[c.info['syntax'].index('Size')] = 0.0
                n += 1
    return n


def flatten(cmds):
    """a script with conditions as straight commands: each condition (IS_FLAG / Float_Compare / Float_Var_Compare) and
    True / Else dropped, the Else branches' commands dropped (True / Else jump Offset words from their own header; a
    command is 1 + its parameters words), EXECUTE dropped (the clone starts its motion at his frame)"""
    pos, at = [], 0
    for c in cmds:
        pos.append(at)
        at += 1 + len(c.params)
    skip = set()
    for i, c in enumerate(cmds):
        if c.name == 'Else':
            end = pos[i] + int(c.params[0])
            for j in range(i + 1, len(cmds)):
                if pos[j] < end:
                    skip.add(j)
    drop = {'IS_FLAG', 'Float_Compare', 'Float_Var_Compare', 'True', 'Else', 'EXECUTE'}
    return [c for i, c in enumerate(cmds) if i not in skip and c.name not in drop]


def clone_scripts(game, effect, mtable_hashes, bmap, joint25=None):
    """the clone article's game / effect scripts: his body's hitbox scripts (bones remapped, his smashes' damage x
    CHARGE_DAMAGE) and their effects (EFFECT / follow / flip / trails only); {crc: [Command]} each"""
    import acmd
    smash = {zlib.crc32(n.encode()) for n in SMASH_SCRIPTS}
    g_out, e_out = {}, {}
    final = {h for i, h in enumerate(mtable_hashes) if i >= FINAL_FIRST}
    for crc in sorted(set(mtable_hashes) - final):
        s = game.scripts.get(crc)
        if not s or not any(c.name in HITBOXES for c in s) or any(c.name in NO_CLONE for c in s):
            eo = clone_effect(effect_jump(effect, crc), bmap, joint25)   # clone fixes v1: no hitbox (a grab, a throw, ...):
            if eo:                                                # its effects anyway
                e_out[crc] = eo
            continue
        inside = spans(s)
        out = []
        for i, c in enumerate(s):
            if i in inside:
                assert c.name in CLONE_GAME | FLOW | FLOW_KEEP_SAFE, 'script 0x%08X: %s in a loop / condition' % (crc, c.name)
            elif c.name not in CLONE_GAME:
                continue
            c2 = acmd.Command(c.ident, list(c.params))
            if c.name in HITBOXES:
                k = param(c2, 'Bone')
                c2.params[k] = bmap(int(c2.params[k]))
                if crc in smash:
                    k = param(c2, 'Damage')
                    c2.params[k] = round(float(c2.params[k]) * CHARGE_DAMAGE, 4)
            out.append(c2)
        g_out[crc] = out
        eo = clone_effect(effect.scripts.get(crc), bmap, joint25)
        if eo:
            e_out[crc] = eo
    for crc, gs in clone_grab(game, bmap).items():        # clone moves v1: grabs, the hold, pummels, throws
        if crc in mtable_hashes:
            g_out[crc] = gs
    for crc, (gs, es) in clone_kick(game, effect, bmap).items():
        if crc in mtable_hashes:
            g_out[crc] = gs
            e_out[crc] = es
    return g_out, e_out


KICK_SCRIPTS = ('speciallwattack', 'specialairlwattack')   # aligned kick v1: the counter's kick (motions 0x279 / 0x28D)
KICK_FLAG = 0x2100001C            # ... its up-diagonal branch (13 %, 60 degrees; clones.c gk_ak_main sets it on him)
KICK_FX_FLAGS = (0x21000018, 0x21000019)   # his effect script's branches the kick plays (False: the flags are off)


# clone moves v1 (the user: "please allow clones to do grabs and throws", "And pummels"): an article can't catch (the
# game's capture needs a fighter grabber), so the clone's grab is hitboxes (its hits are his): his grab boxes (catch,
# catchdash, catchturn: Extended_Grab_Collision) as hold hitboxes (0 %, 361, BKB GRAB_HOLD_BKB: 16 frames of hitstun,
# hitlag 0, not shieldable, Hitbox_Hold mode 2: the victim stays where it is), CatchWait the hold at its hand again every
# GRAB_REHIT frames, his pummel (CatchAttack's 2 % hitbox) not shieldable and held, his throws (ThrowF / B / Hi / Lw:
# their Throw_Specifier Kind 0 damage / angle / KBG / WBKB / BKB) a hitbox at the hold on their Throw_Applier frame.
# The clones play these motions with him (formation; split: mirroring his grab), so the hold lasts his grab's time
GRAB_HOLD_BKB = 40
GRAB_REHIT = 12
GRAB_AT = (0.0, 6.0, 12.0, 7.0)          # the hold's place (X, Y, Z) and size (his grab boxes reach Z 16 - 22 at Y 6)
GRAB_SCRIPTS = ('catch', 'catchdash', 'catchturn')
THROW_SCRIPTS = ('throwf', 'throwb', 'throwhi', 'throwlw')


def clone_grab(game, bmap):
    """{crc: [Command]}: the clone's catch / catchwait / catchattack / throw game scripts"""
    import acmd
    SPECIAL, EXT, HOLD = 0x14FCC7E4, 0x7075DC5A, 0xAB0FC57C
    REMOVE, END, FRAME, WAIT = 0x9245E1A8, 0x5766F889, 0x42ACFE7D, 0x4B7B6E51
    pum = next(c for c in game.scripts[acmd.crc('catchattack')] if c.ident == SPECIAL)

    def box(hid, dmg, ang, kbg, fkb, bkb, at, rehit=0, hitlag=0.0, ext=None, src=pum, bone=0):
        c = acmd.Command(SPECIAL, list(src.params))
        for nm, v in (('ID', hid), ('Bone', bmap(bone)), ('Damage', dmg), ('Angle', ang), ('KBG', kbg), ('FKB', fkb),
                      ('BKB', bkb), ('Size', at[3]), ('X', at[0]), ('Y', at[1]), ('Z', at[2]), ('Hitlag', hitlag),
                      ('Shieldable', 0), ('Rehit', rehit), ('NoGrabRelease', 1)):
            c.params[param(c, nm)] = v
        if ext is not None:
            c = acmd.Command(EXT, c.params[:40] + list(ext))
        return [c, acmd.Command(HOLD, [hid, 2])]

    def hold(hid, rehit=GRAB_REHIT):
        return box(hid, 0.0, 361, 0, 0, GRAB_HOLD_BKB, GRAB_AT, rehit)
    out = {}
    for n in GRAB_SCRIPTS:
        g = []
        for c in game.scripts[acmd.crc(n)]:
            if c.ident in (FRAME, WAIT):
                g.append(acmd.Command(c.ident, list(c.params)))
            elif c.name == 'Extended_Grab_Collision':
                p_ = lambda nm: c.params[c.info['syntax'].index(nm)]
                g += box(int(p_('ID')), 0.0, 361, 0, 0, GRAB_HOLD_BKB, (p_('X'), p_('Y'), p_('Z'), p_('Size')),
                         ext=(p_('X2'), p_('Y2'), p_('Z2')), bone=int(p_('Bone')))
            elif c.name == 'Remove_All_Grab_Collisions':
                g.append(acmd.Command(REMOVE, []))
        out[acmd.crc(n)] = g + [acmd.Command(END, [])]
    out[acmd.crc('catchwait')] = hold(0) + [acmd.Command(END, [])]
    ps = game.scripts[acmd.crc('catchattack')]
    f = next(int(c.params[0]) for c in ps if c.ident == FRAME)
    pm = acmd.Command(SPECIAL, list(pum.params))
    pm.params[param(pm, 'Bone')] = bmap(int(pm.params[param(pm, 'Bone')]))
    pm.params[param(pm, 'Shieldable')] = 0
    pm.params[param(pm, 'ID')] = 1
    out[acmd.crc('catchattack')] = hold(0, 0) + [acmd.Command(FRAME, [f]), pm, acmd.Command(HOLD, [1, 2]),
                                                  acmd.Command(WAIT, [1]), acmd.Command(REMOVE, [])] + hold(0, 0) + \
        [acmd.Command(END, [])]
    for n in THROW_SCRIPTS:
        ts = game.scripts[acmd.crc(n)]
        sp = next(c for c in ts if c.name == 'Throw_Specifier' and int(c.params[0]) == 0)
        q = lambda nm: sp.params[sp.info['syntax'].index(nm)]
        rel = 0
        for c in ts:
            if c.name == 'FRAME':
                rel = int(c.params[0])
            if c.name == 'Throw_Applier':
                break
        th = box(0, q('Damage'), int(q('Angle')), int(q('KBG')), int(q('WBKB')), int(q('BKB')), GRAB_AT, hitlag=1.0)[:1]
        out[acmd.crc(n)] = hold(1, 0) + [acmd.Command(FRAME, [rel]), acmd.Command(REMOVE, [])] + th + \
            [acmd.Command(WAIT, [1]), acmd.Command(REMOVE, []), acmd.Command(END, [])]
    return out


def kick_branch(s, flag):
    """the Hitbox commands of `IS_FLAG(flag)`'s True branch in his counter kick's game script"""
    i = next(i for i, c in enumerate(s) if c.name == 'IS_FLAG' and int(c.params[0]) == flag)
    assert s[i + 1].name == 'True'
    out = []
    for c in s[i + 2:]:
        if c.name not in HITBOXES:
            break
        out.append(c)
    assert out
    return out


def clone_kick(game, effect, bmap):
    """aligned kick v1: the clone's counter kick (its game scripts skip IS_FLAG scripts): his first FRAME (the kick at 5),
    the up-diagonal branch's hitboxes (bones as the article's), his last FRAME / Remove_All_Hitboxes; its effects: his
    effect script's commands under the False branches it plays (his flags 0x21000018 / 19 off); {crc: (game, effect)}"""
    import acmd
    s = game.scripts[acmd.crc(KICK_SCRIPTS[0])]
    frames = [c for c in s if c.name == 'FRAME']
    g = [acmd.Command(frames[0].ident, list(frames[0].params))]
    for c in kick_branch(s, KICK_FLAG):
        c2 = acmd.Command(c.ident, list(c.params))
        k = param(c2, 'Bone')
        c2.params[k] = bmap(int(c2.params[k]))
        g.append(c2)
    g.append(acmd.Command(frames[-1].ident, list(frames[-1].params)))
    rm = [c for c in s if c.name == 'Remove_All_Hitboxes']
    g.append(acmd.Command(rm[-1].ident, []))
    g.append(acmd.Command(s[-1].ident, []))
    assert s[-1].name == 'Script_End'
    e = []
    for c in effect.scripts[acmd.crc(KICK_SCRIPTS[0])]:
        if c.name in ('IS_FLAG', 'False', 'ON_FLAG', 'True', 'Else'):
            continue
        c2 = acmd.Command(c.ident, list(c.params))
        if c.name not in ('FRAME', 'WAIT'):
            assert c.name in CLONE_EFFECT, c.name
            for nm in ('Bone', 'Bone1', 'Bone2', 'Bone3'):
                if nm in c2.info['syntax']:
                    k = param(c2, nm)
                    c2.params[k] = bmap(int(c2.params[k]))
        e.append(c2)
    assert e[-1].name == 'Script_End'
    return {acmd.crc(n): (g, e) for n in KICK_SCRIPTS}


def effect_jump(effect, crc):
    """clone fix v3 (the user: split clones' effects missing): his effect script for crc, or, when it is only a JUMP to
    another script (his double jumps -> JumpF's, the aerials' landings -> the landing's: their dust), that script"""
    e = effect.scripts.get(crc)
    if e and [c.name for c in e if c.name != 'Script_End'] == ['JUMP']:
        return effect.scripts.get(int(e[0].params[0]))
    return e


def clone_effect(e, bmap, joint25=None):
    """one motion's effect script for the clone: its conditions' True branches (v4: the smashes'; clone fixes v1: every
    script's), CLONE_EFFECT's commands with their joints remapped; None when it calls / jumps / loops or has no effect"""
    import acmd
    if not e or any(c.name in CLONE_EFFECT_SKIP for c in e):
        return None
    eo = []
    for c in flatten(e):
        if c.name not in CLONE_EFFECT:
            continue
        c2 = acmd.Command(c.ident, list(c.params))
        try:
            for nm in ('Bone', 'Bone1', 'Bone2', 'Bone3'):
                if nm in c2.info['syntax']:
                    k = param(c2, nm)
                    j = int(c2.params[k])
                    c2.params[k] = joint25 if (joint25 is not None and j == 25) else bmap(j)
        except (IndexError, AssertionError):
            continue                      # a joint past his model.jtb's tables: left out (none of the attacks')
        eo.append(c2)
    if any(c.name not in ('FRAME', 'WAIT', 'Script_End') for c in eo):
        return eo
    return None


# burn v2: fire at the outer ends of his water (his bank's PtcGekkougaFireTip, fire_torch_012: a looping billboard flame
# centred on the call). The water sword (0x3300007, External_Graphic on a hand: 24 / 25) ends where its trail's second
# point is (Sword_Glow Y2: -11 x its size: -55 in the smashes at x5, -11 in forward air): a flame there on each sword,
# made with it, ended with it (the sword's Terminate_Graphic_Effect). Neutral air's water burst (0x330000B at joint 0,
# Y 8.5): a flame each side (Z +- FIRE_NAIR_Z), ended at frame FIRE_NAIR_END. Up smash's water is the two hand swords
# (the EffGekkougaAttackHi model 0x3300011 is up tilt's, not up smash's: his effect.bin)
FIRE_TIPS = True                  # (False: skeleton v1.2's scripts, without them)
FIRE_TIP = 0x330001B
SWORD = 0x3300007
SWORD_LEN = 11.0                  # the sword at size 1 (forward air's trail: Y2 -11; the smashes' -55 at x5)
FIRE_TIP_SIZE = {'AttackS4': 2.0, 'AttackHi4': 2.0, 'AttackLw4': 2.0}   # (burn v2 - aerial chain v1: AttackAirF 0.7 too)
FIRE_BLADE = 0x3300022            # skeleton v1.3 package (the user: "make forward air have more fire along the edges of the
                                  # water blade and make the fire larger"): his bank's PtcGekkougaFireBlade, flames along
                                  # the sword (tools/gekkouga_fx.py FIRE_BLADE), called at the sword's own joint and size
                                  # in place of forward air's tip flame, ended with the sword
FIRE_BLADE_SCRIPTS = ('AttackAirF',)
NAIR_BURST = 0x330000B
FIRE_NAIR_Z = 10.0                # (burn v2 - v2.1: a flame each side, Z +- 10, ended at 24)
FIRE_NAIR_Y = 8.5
FIRE_NAIR_SIZE = 1.0
FIRE_NAIR_END = 24
FIRE_RING = 0x330001D             # burn v2.2 (the user: "wrap neutral air's water edges in fire"): his bank's
                                  # PtcGekkougaFireRing, a ring of 15 flames round the water burst's edge, growing with it
                                  # (tools/gekkouga_fx.py FIRE_RING), made with the burst: the burst's call (joint 0, Y 8.5,
                                  # size 1.45), played out (no Terminate: one-shot flames). v2.3: each flame its own
                                  # footage, turned out from his centre: EFFECT_FOLLOW_FLIP with the left-facing set
FIRE_RING_L = 0x330001E           # PtcGekkougaFireRingL (the game mirrors the places facing left, not a billboard's turn)


def insert_cmds(cmds, i, new):
    """new commands before cmds[i], inside every True / Else / False block that holds cmds[i] (their Offset words grow)"""
    pos, at = [], 0
    for c in cmds:
        pos.append(at)
        at += 1 + len(c.params)
    q = pos[i] if i < len(cmds) else at
    words = sum(1 + len(c.params) for c in new)
    for j, c in enumerate(cmds):
        if c.name in ('True', 'Else', 'False') and pos[j] < q < pos[j] + int(c.params[0]):
            c.params[0] = int(c.params[0]) + words
    cmds[i:i] = new


def ext_graphic(gfx, bone, x, y, z, size, terminate=1):
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['External_Graphic']
    vals = dict(Graphic=gfx, Bone=bone, X=x, Y=y, Z=z, XRot=0.0, YRot=0.0, ZRot=0.0, Size=size, Terminate=terminate)
    return acmd.Command(ident, [vals[n] for n in acmd.INFO[ident]['syntax']])


def follow_flip(right, left, bone, x, y, z, size):
    """EFFECT_FOLLOW_FLIP (the facing's id: right / left), as vanilla's (up tilt's: Terminate 1, FlipType 1)"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['EFFECT_FOLLOW_FLIP']
    vals = dict(GFXRight=right, GFXLeft=left, Bone=bone, X=x, Y=y, Z=z, XRot=0.0, YRot=0.0, ZRot=0.0, Size=size, Terminate=1,
                FlipType=1)
    return acmd.Command(ident, [vals[n] for n in acmd.INFO[ident]['syntax']])


def terminate_gfx(gfx):
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['Terminate_Graphic_Effect']
    vals = dict(Graphic=gfx, KillParticles=0, KillImmediately=0)
    return acmd.Command(ident, [vals[n] for n in acmd.INFO[ident]['syntax']])


def add_fire_tips(effect):
    """burn v2: the flames at his water's ends (after scale_smash: the sizes / offsets are the scaled ones)"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    n = 0
    for name, size in FIRE_TIP_SIZE.items():
        s = effect.script(name)
        i = 0
        while i < len(s):
            c = s[i]
            syn = c.info['syntax']
            if c.name == 'External_Graphic' and int(c.params[0]) == SWORD:
                y = -SWORD_LEN * float(c.params[syn.index('Size')])
                insert_cmds(s, i, [ext_graphic(FIRE_TIP, int(c.params[syn.index('Bone')]), 0.0, y, 0.0, size)])
                i += 2
                n += 1
                continue
            if c.name == 'Terminate_Graphic_Effect' and int(c.params[0]) == SWORD:
                insert_cmds(s, i, [terminate_gfx(FIRE_TIP)])
                i += 2
                continue
            i += 1
    for name in FIRE_BLADE_SCRIPTS:
        s = effect.script(name)
        i = 0
        while i < len(s):
            c = s[i]
            syn = c.info['syntax']
            if c.name == 'External_Graphic' and int(c.params[0]) == SWORD:
                insert_cmds(s, i, [ext_graphic(FIRE_BLADE, int(c.params[syn.index('Bone')]), 0.0, 0.0, 0.0,
                                               float(c.params[syn.index('Size')]))])
                i += 2
                n += 1
                continue
            if c.name == 'Terminate_Graphic_Effect' and int(c.params[0]) == SWORD:
                insert_cmds(s, i, [terminate_gfx(FIRE_BLADE)])
                i += 2
                continue
            i += 1
    s = effect.script('AttackAirN')
    i = [k for k, c in enumerate(s) if c.name == 'External_Graphic' and int(c.params[0]) == NAIR_BURST][0]
    b = s[i]
    syn = b.info['syntax']
    insert_cmds(s, i + 1, [follow_flip(FIRE_RING, FIRE_RING_L, int(b.params[syn.index('Bone')]), 0.0,
                                       float(b.params[syn.index('Y')]), float(b.params[syn.index('Z')]),
                                       float(b.params[syn.index('Size')]))])
    return n + 1


def remove_cmd(cmds, i):
    """cmds[i] removed (insert_cmds undone: the True / Else / False blocks holding it shrink)"""
    pos, at = [], 0
    for c in cmds:
        pos.append(at)
        at += 1 + len(c.params)
    words = 1 + len(cmds[i].params)
    for j, c in enumerate(cmds):
        if c.name in ('True', 'Else', 'False') and pos[j] < pos[i] < pos[j] + int(c.params[0]):
            c.params[0] = int(c.params[0]) - words
    del cmds[i]


def strip_fire_tips(effect):
    """add_fire_tips undone (tests: the rest of his scripts as before): its commands, and neutral air's FRAME before
    its Terminate"""
    n = 0
    for crc, cmds in effect.scripts.items():
        i = 0
        while i < len(cmds):
            c = cmds[i]
            if c.name in ('External_Graphic', 'Terminate_Graphic_Effect', 'EFFECT_FOLLOW_FLIP') and \
                    int(c.params[0]) in (FIRE_TIP, FIRE_RING, FIRE_BLADE):
                if c.name == 'Terminate_Graphic_Effect' and i and cmds[i - 1].name == 'FRAME' and \
                        float(cmds[i - 1].params[0]) == FIRE_NAIR_END and i + 1 < len(cmds) and \
                        cmds[i + 1].name == 'Script_End':          # neutral air's own FRAME (not a sword's at 24)
                    remove_cmd(cmds, i - 1)
                    i -= 1
                remove_cmd(cmds, i)
                n += 1
                continue
            i += 1
    return n


def add_rolloff(game):
    """skeleton v1.3: his rolls' roll-off speed (tools/rolloff_acmd.py --plain --add ROLLOFF_SPEED EscapeF EscapeB: the
    back roll -speed), where a roll has none yet"""
    import acmd
    import rolloff_acmd as RA
    for nm in ROLLOFF_SCRIPTS:
        sc = game.scripts.setdefault(acmd.crc(nm), [])
        if any(c.ident == RA.MOM and float(c.params[0]) != 0 for _f, c in RA.timeline(sc)):
            continue
        RA.add_speed(sc, -ROLLOFF_SPEED if nm == 'EscapeB' else ROLLOFF_SPEED, 5.0, 27.0, scripts=game.scripts)


# clone fixes v2 (the user: "Clones also still display trails incorrectly": forward air's sword / trail / flames hang
# straight down on the clones, sweep on him): his effects on joint 25 (the water sword's in forward air and the smashes)
# are model.jtb table 0's entry 25 = ThrowN, which no motion of his moves (main.pac's track constant, no part pac has it),
# so the clone's copy stays still; on him something native moves it (not found). TEST_ONLY_DATA/<name>: the clone's
# effect.bin with joint 25 on one of his hands instead, for the user to pick
CLONE_JOINT25_TESTS = ()          # (skeleton v1.4: clone_sword_rhave / clone_sword_thrown; settled: none)


# ---------------------------------------------------------------- tuning v1 (the user: "Can you make forward smash longer
# (not bigger) so it reaches Donkey Kong ... remove the shield break effect from neutral air and make it 25% larger, also
# remove the forward tilt teleporting code")
FTILT_TELEPORT = 0x0F00000C       # the position variable his attacks3 set to 12 at its hit (his own script, the user's
                                  # data): "put the opponent 12 in front of self" (docs/position-variables.md): the teleport
NAIR_SHIELDBREAK = 0x0F0000B2     # LASTHIT_STATUS: his neutral air's second hit set the fighter it hit to 89 (0x59, shield
                                  # break: its burst, its dizziness)
NAIR_SCALE = 1.25                 # its hitboxes' and its burst / fire ring's size
FSMASH_EXTRA = 30.0               # forward smash's blade this much longer (its width the same): a second water sword
                                  # (0x3300007, the same size) from this far along the blade, its trail and its tip flame
                                  # at the new end (55 -> 85), a hitbox further out (the first's size, at 32.5 + 30)
FSMASH_BLADE = 55.0


# ---------------------------------------------------------------- neutral air ring v1 (the user: "increase neutral air's
# hitbox size, and make the outer fire ring into weak hitboxes that can connect from the stronger hit")
NAIR_STRONG = 12.0                # its strong hits' size (11 %, frames 12-14 and the connected re-hit 17-19; tuning v1
                                  # 9.375): the water burst's solid disc as drawn (fx_render at 1.8125: its light >= 80 %
                                  # out to 11.5 - 12.5 at frames 12-15)
NAIR_LATE = 14.0                  # its late hit's size (6 %, frames 14-17; tuning v1 12.5): the burst's drawn edge (its
                                  # light ~0.6 at 13 - 14, 80 % of it inside 14.6 - 15.3 at frames 13-16)
NAIR_FX_FRAME = 11                # the burst / ring's call frame (his effect script)
NAIR_FX_Y = 8.5                   # ... at joint 0, Y 8.5 (the ring's centre)
NAIR_FX_SIZE = 1.8125             # ... its size (tuning v1)
NAIR_RING_PART = 0                # the ring's boxes: Part 0, the burst's (smash tune v1; nair ring v1: Part 1, their own hit
                                  # record): one record for the burst and the ring, so a fighter the burst hit is never touched
                                  # by the ring (its launch kept) and the ring pushes anyone else once. set_attack (0x02C08848)
                                  # keeps a Part's record while an ID set again is still out on it and clears it when a new ID
                                  # is set on that Part: the ring's IDs are all set at 12 with the burst's (NAIR_RING_START),
                                  # then only moved (docs/native-notes.md)
NAIR_RING_IDS = (1, 2, 3, 4, 5, 6)   # 6 capsules (a hexagon round the ring): the clone (a weapon: IDs 0-6, Parts 0-1)
                                  # plays this script too
NAIR_RING_START = 12              # smash tune v1: set with the burst's first hit (12), tucked inside it (NAIR_RING_TUCK) until
NAIR_RING_TUCK = 8.0              # 14: corners 8 from the ring's centre (joint 0, Y 8.5), + the capsules' 2.5: inside the
                                  # burst's 12 round joint 3 (at Z 0.9, Y 8.5 - 8.7 at 12 - 13 in his motion: at most 11.4
                                  # from it): whatever they touch the burst (ID 0, the lower ID: it wins a shared frame)
                                  # touches too
NAIR_RING_FRAMES = (14, 16, 18, 20, 22)   # out along the ring from 14, moved every 2 frames (the same IDs, still out: the
NAIR_RING_END = 24                # record kept), gone at 24 (the ring's flames: called at 11, 14 frames, under 15 % alpha by 24)
NAIR_RING_TIP = 4.5               # the ring's flames' lit tips past their centres (fx_render: 4.3 - 4.7 at frames 14-19)
NAIR_RING_MIN = 2.5               # the capsules' least radius
NAIR_RING_HIT = dict(Damage=0.0, Angle=361, KBG=100, FKB=10, BKB=0, Effect=5, Trip=0.0, Hitlag=0.0, SDI=0.0, Clang=0,
                     Rebound=0, ShieldDamage=0, SFXLevel=0, SFXType=0, Type=0, HitBits=0x3F, Unk41=0, CollisionPart=0xF,
                     NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0,
                     FacingRestrict=0, NoGrabRelease=0, TeamDamage=0, DisableHitlag=1, NoGFX=1, Flinchless=1)
                                  # smash tune v1 (the user: "Please remove any knockback from the fire ring and turn it into a
                                  # very weak windbox"): Smash 4's windbox, as F.L.U.D.D.'s water (Mario's pumpwater game.bin:
                                  # Special_Hitbox, 0 %, KBG 100, set knockback (FKB) 50 / 58, BKB 0, Flinchless 1 (no
                                  # reaction: a push, no hitstun / tumble), NoGFX 1): 0 %, set knockback 10 (KB ((1 + 10 / 2) x
                                  # 1.4 + 18) x 1 = 26.4 at weight 100: about 0.8 a frame, F.L.U.D.D.'s 54.4), angle 361 by
                                  # position (FacingRestrict 0: away from him either side), DisableHitlag 1 (no hitlag either
                                  # side), no clank, no sound, fire (element 5), shieldable (as F.L.U.D.D.: 0 shield damage).
                                  # Nair ring v1: 2.5 %, angle 60, KBG / BKB 25, hitlag 0.5


def ring_radius(frame, ring=None):
    """the ring's flames' centres' radius at a frame (tools/gekkouga_fx.py FIRE_RING: r0 + v (1 - air^t) / (1 - air), t
    the frames since the call less one, x the call's size); fx_render's light centre is within ~1.5 of it"""
    import gekkouga_fx
    r = ring or gekkouga_fx.FIRE_RING
    t = max(0, frame - NAIR_FX_FRAME - 1)
    return NAIR_FX_SIZE * (r['r0'] + r['v'] * (1 - r['air'] ** t) / (1 - r['air']))


def ring_stage(frame):
    """(hexagon vertex radius, capsule radius) of the ring boxes set at frame (held to frame + 1): the band from the burst
    boxes' edge (NAIR_LATE) to the flames' tips at frame + 1, its middle the hexagon's mean radius ((1 + cos 30) / 2 of
    the vertices'), half its width the capsules' (at least NAIR_RING_MIN)"""
    ri, ro = NAIR_LATE, ring_radius(frame + 1) + NAIR_RING_TIP
    return round((ri + ro) / 2 / ((1 + math.cos(math.radians(30))) / 2), 2), round(max(NAIR_RING_MIN, (ro - ri) / 2), 2)


def ring_boxes(frame):
    """the 6 Extended_Special_Hitbox windbox capsules (Part 0, joint 0) of the ring at frame: hexagon edges round (0,
    NAIR_FX_Y); at NAIR_RING_START tucked inside the burst (NAIR_RING_TUCK)"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['Extended_Special_Hitbox']
    rv, sz = (NAIR_RING_TUCK, NAIR_RING_MIN) if frame == NAIR_RING_START else ring_stage(frame)
    out = []
    for k, hid in enumerate(NAIR_RING_IDS):
        a0, a1 = math.radians(60 * k), math.radians(60 * (k + 1))
        vals = dict(NAIR_RING_HIT, ID=hid, Part=NAIR_RING_PART, Bone=0, Size=sz,
                    X=0.0, Y=round(NAIR_FX_Y + rv * math.sin(a0), 3), Z=round(rv * math.cos(a0), 3),
                    X2=0.0, Y2=round(NAIR_FX_Y + rv * math.sin(a1), 3), Z2=round(rv * math.cos(a1), 3))
        vals['Ground/Air'], vals['Direct/Indirect'], vals['Type'] = 3, 1, 0
        out.append(acmd.Command(ident, [vals[n] for n in acmd.INFO[ident]['syntax']]))
    return out


def nair_ring(game):
    """neutral air: the strong / late hits NAIR_STRONG / NAIR_LATE, and the ring's windbox capsules (smash tune v1: Part 0,
    set at 12 inside the burst, out along the ring from 14 to 24; nair ring v1: weak hits, Part 1, 14 - 24) on absolute
    FRAMEs; his WAITs become FRAMEs (the same frames), the end Remove_All_Hitboxes (19) Remove_Hitbox(0)"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    s = game.scripts[acmd.crc('attackairn')]
    hb = [c for c in s if c.name in HITBOXES]
    assert [float(c.params[param(c, 'Damage')]) for c in hb] == [11.0, 6.0, 11.0], hb
    for c in hb:
        c.params[param(c, 'Size')] = NAIR_LATE if float(c.params[param(c, 'Damage')]) == 6.0 else NAIR_STRONG
    on, cmp_, tr = (next(c for c in s if c.name == n) for n in ('ON_FLAG', 'Float_Var_Compare', 'True'))
    off = next(c for c in s if c.name == 'OFF_FLAG')
    assert int(tr.params[0]) == 2 + 1 + len(hb[2].params), 'the True block: the re-hit only'
    fr = lambda n: acmd.Command(by['FRAME'], [float(n)])
    rm = acmd.Command(by['Remove_Hitbox'], [0])
    new = [fr(10), on, fr(12), hb[0]] + ring_boxes(NAIR_RING_START) + [fr(14), hb[1]] + ring_boxes(14) + [fr(16)] + \
          ring_boxes(16) + \
          [fr(17), cmp_, tr, hb[2], fr(18)] + ring_boxes(18) + [fr(19), rm, fr(20)] + ring_boxes(20) + [fr(22)] + \
          ring_boxes(22) + [fr(NAIR_RING_END), acmd.Command(by['Remove_All_Hitboxes'], []), fr(40), off,
                            acmd.Command(by['Script_End'], [])]
    s[:] = new


# ---------------------------------------------------------------- forward air reach (the user: "Can you also extend
# forward air's length to hit Donkey Kong?"): as forward smash in tuning v1, longer not bigger
FAIR_EXTRA = 10.0                 # a second water sword (0x3300007, size 1: 11 long) from 10 along the blade (11 -> 21), its
                                  # FireBlade flames with it (a second 0x3300022 call there), the Sword_Glow trail to -21, a
                                  # hitbox ID 2 (ID 0's) at Y -17: reach 22.4 from the hand (was 12.4). The user's screenshot
                                  # ($S/gk_in/clone_fx/fair_reach.png; the blade 11 = ~122 px, his leg ~ the same scale:
                                  # 11.1 px a unit): DK's nearest point 221 px = 19.9 from his hand
FAIR_BLADE = 11.0


def fair_reach(game, effect):
    import acmd
    g = game.scripts[acmd.crc('attackairf')]
    h0 = next(c for c in g if c.name in HITBOXES and int(c.params[param(c, 'ID')]) == 0)
    h1 = next(c for c in g if c.name in HITBOXES and int(c.params[param(c, 'ID')]) == 1)
    h2 = acmd.Command(h0.ident, list(h0.params))
    h2.params[param(h2, 'ID')] = 2
    h2.params[param(h2, 'Y')] = round(float(h0.params[param(h0, 'Y')]) - FAIR_EXTRA, 4)
    insert_cmds(g, g.index(h1) + 1, [h2])
    r1 = next((c for c in g if c.name == 'ATK_RESERVE' and int(c.params[0]) == 1), None)
    if r1 is not None:
        r0 = next(c for c in g if c.name == 'ATK_RESERVE' and int(c.params[0]) == 0)
        r2 = acmd.Command(r0.ident, list(r0.params))
        r2.params[0] = 2
        r2.params[param(r2, 'Y')] = round(float(r0.params[param(r0, 'Y')]) - FAIR_EXTRA, 4)
        insert_cmds(g, g.index(r1) + 1, [r2])
    e = effect.scripts[acmd.crc('attackairf')]
    for gfx in (FIRE_BLADE, SWORD):
        k = next(i for i, c in enumerate(e) if c.name == 'External_Graphic' and int(c.params[0]) == gfx)
        c2 = acmd.Command(e[k].ident, list(e[k].params))
        c2.params[param(c2, 'Y')] = -FAIR_EXTRA
        insert_cmds(e, k + 1, [c2])
    for c in e:
        if c.name == 'Sword_Glow':
            c.params[param(c, 'Y2')] = -(FAIR_BLADE + FAIR_EXTRA)


# ---------------------------------------------------------------- smash tune v1: up smash's weak spike (the user: "Please make
# up smash do a weak spike if they are on the inner hit of the part with both swords going downwards"; "The up smash spike
# should send at a diagonal angle away from Greninja"). His AttackHi4 (motion 99, the user's script): at 18 the geyser (ID
# 0, Y 27, 14 %, until 19) and both swords as they sweep down from overhead to his sides (his motion: the hands' -Y, the
# swords, from straight up at 15 to level at 18 and below level at 19 - 20; out until 21): on each sword (bones 0x19 /
# 0x18) an outer hit 20 along it (size 23.5) and an inner one at the hand (Y 0, size 17.5: nearer his body), 11 %, 44
# degrees. Smash 4 gives an overlap to the lowest ID, and the outer spheres covered most of the inner ones (the inner
# hits were IDs 3 / 4): now the inner ones are IDs 1 / 2 (the outer ones 3 / 4, their ATK_RESERVEs too), so whoever is
# in an inner sphere at 19 - 20 is spiked (at 18 the geyser, ID 0, still wins), and the inner hits are the spike:
USMASH_SPIKE = dict(Angle=300, KBG=50, FKB=0, BKB=25)
                                  # 300 degrees: down and away at 60 below level, by position (a plain Hitbox's facing
                                  # restriction is the AttackModule's default, +0x11A = 0: Ultimate's LR_CHECK_POS, the
                                  # victim's side of him), so behind him it goes down and back (240 on screen); weak: KBG 50
                                  # / BKB 25 (11 %, weight 100: KB 39 at 0 %, 84 at 100 %, 107 at 150 %: no tumble (80)
                                  # under about 95 %; was 44 degrees, KBG 100, BKB 30)
USMASH_SPIKE_FRAME = 18
# usmash spike v2 (the user: "Can you make all of the strong part of Up smash's hitbox do the spike?", "the outer hits were
# knocking back rather than spiking"): the strong part is every hitbox his AttackHi4 sets at 18 (the only frame from 15
# to 21 that sets one): the geyser (ID 0, Part 1, 14 %, Y 27 on joint 0, off at 19) and the four sword hits (inner 1 / 2,
# outer 3 / 4, 11 %, off at 21): frames 18 - 20. All five now take USMASH_SPIKE (angle 300 by position, KBG 50, FKB 0,
# BKB 25); their damage (uncharged), size, place, Part and the rest kept. Left as they are: the first weak hit (ID 0, Part
# 0, 5 %, angle 366, 12 - 17) before it and the late capsule (Extended_Hitbox ID 1, 10 %, 40 degrees, 21) after it
USMASH_STRONG = (18, 21)          # [set, all off): the strong part's frames 18, 19, 20


def usmash_spike(game):
    import acmd
    s = game.scripts[acmd.crc('attackhi4')]
    at, fr, hits = 0.0, {}, []
    for c in s:
        if c.name == 'FRAME':
            at = float(c.params[0])
        if c.name in HITBOXES and at == USMASH_SPIKE_FRAME and int(c.params[param(c, "Bone")]) in SWORD_BONES:
            hits.append(c)
    assert len(hits) == 4 and sorted(int(c.params[param(c, 'ID')]) for c in hits) == [1, 2, 3, 4], hits
    inner = sorted((c for c in hits if abs(float(c.params[param(c, 'Y')])) < 1e-6), key=lambda c: -int(c.params[param(c, 'Bone')]))
    outer = sorted((c for c in hits if abs(float(c.params[param(c, 'Y')])) >= 1e-6), key=lambda c: -int(c.params[param(c, 'Bone')]))
    assert len(inner) == 2 and len(outer) == 2
    new_id = {}
    for k, c in enumerate(inner + outer):            # inner 1 (0x19), 2 (0x18); outer 3 (0x19), 4 (0x18)
        new_id[(int(c.params[param(c, 'Bone')]), k < 2)] = k + 1
        c.params[param(c, 'ID')] = k + 1
    strong = [c for c in usmash_strong(s) if c not in hits]
    assert len(strong) == 1 and int(strong[0].params[param(strong[0], 'ID')]) == 0 and \
        int(strong[0].params[param(strong[0], 'Bone')]) == 0, strong          # the geyser
    for c in inner + outer + strong:                 # usmash spike v2: the whole strong part (v1: inner only)
        for nm, v in USMASH_SPIKE.items():
            c.params[param(c, nm)] = v
    for c in s:                                      # the reserves at 15 (unscaled offsets: inner Y 0, outer Y -4)
        if c.name == 'ATK_RESERVE' and int(c.params[0]) in (1, 2, 3, 4):
            c.params[0] = new_id[(int(c.params[param(c, 'Bone')]), abs(float(c.params[param(c, 'Y')])) < 1e-6)]


def usmash_strong(script):
    """usmash spike v2: the hitbox commands of AttackHi4's strong part (those set in USMASH_STRONG's frames)"""
    at, out = 0.0, []
    for c in script:
        if c.name == 'FRAME':
            at = float(c.params[0])
        elif c.name == 'WAIT':
            raise AssertionError('AttackHi4: a WAIT (the strong part is read on absolute FRAMEs)')
        if c.name in HITBOXES and USMASH_STRONG[0] <= at < USMASH_STRONG[1]:
            out.append(c)
    return out


def remove_cmds(cmds, keep):
    """cmds without those keep() refuses, every True / Else / False block that held one shorter by its words"""
    while True:
        pos, at = [], 0
        for c in cmds:
            pos.append(at)
            at += 1 + len(c.params)
        k = next((i for i, c in enumerate(cmds) if not keep(c)), None)
        if k is None:
            return
        w = 1 + len(cmds[k].params)
        for j, c in enumerate(cmds):
            if c.name in ('True', 'Else', 'False') and pos[j] < pos[k] < pos[j] + int(c.params[0]):
                c.params[0] = int(c.params[0]) - w
        del cmds[k]


def tune(game, effect):
    import acmd
    remove_cmds(game.scripts[acmd.crc('attacks3')],
                lambda c: not (c.name == 'SET_FLOAT' and int(c.params[1]) == FTILT_TELEPORT))
    s = game.scripts[acmd.crc('attackairn')]
    remove_cmds(s, lambda c: not (c.name == 'SET_FLOAT' and int(c.params[1]) == NAIR_SHIELDBREAK))
    for c in s:
        if c.name in HITBOXES:
            c.params[param(c, 'Size')] = round(float(c.params[param(c, 'Size')]) * NAIR_SCALE, 4)
    for c in effect.scripts[acmd.crc('attackairn')]:
        if 'Size' in c.info['syntax']:
            c.params[param(c, 'Size')] = round(float(c.params[param(c, 'Size')]) * NAIR_SCALE, 4)
    nair_ring(game)
    fair_reach(game, effect)
    usmash_spike(game)
    g = game.scripts[acmd.crc('attacks4')]
    h0 = next(c for c in g if c.name in HITBOXES and int(c.params[param(c, 'ID')]) == 0)
    h3 = acmd.Command(h0.ident, list(h0.params))
    h3.params[param(h3, 'ID')] = 3
    h3.params[param(h3, 'Y')] = round(float(h0.params[param(h0, 'Y')]) - FSMASH_EXTRA, 4)
    insert_cmds(g, g.index(h0) + 1, [h3])
    e = effect.scripts[acmd.crc('attacks4')]
    for c in e:
        if c.name == 'External_Graphic' and int(c.params[0]) == FIRE_TIP:
            c.params[param(c, 'Y')] = -(FSMASH_BLADE + FSMASH_EXTRA)
        if c.name == 'Sword_Glow':
            c.params[param(c, 'Y2')] = -(FSMASH_BLADE + FSMASH_EXTRA)
    k = next(i for i, c in enumerate(e) if c.name == 'External_Graphic' and int(c.params[0]) == SWORD)
    c2 = acmd.Command(e[k].ident, list(e[k].params))
    c2.params[param(c2, 'Y')] = -FSMASH_EXTRA
    insert_cmds(e, k + 1, [c2])


def cmd_acmd(user_dir, vanilla_model, out_dir, test_only=None):
    """user_dir: his script/animcmd (body/ game, effect, sound, expression, motion.mtable); vanilla_model: his
    model/body/c00 (model.jtb / model.vbn for the clone's joints); out_dir: script/animcmd of the package"""
    import acmd
    body = os.path.join(user_dir, 'body')
    game = acmd.ACMDFile.load(os.path.join(body, 'game.bin'))
    effect = acmd.ACMDFile.load(os.path.join(body, 'effect.bin'))
    n = scale_smash(game, effect)
    add_rolloff(game)
    tips = add_fire_tips(effect) if FIRE_TIPS else 0
    tune(game, effect)
    ob = os.path.join(out_dir, 'body')
    os.makedirs(ob, exist_ok=True)
    game.save(os.path.join(ob, 'game.bin'))
    effect.save(os.path.join(ob, 'effect.bin'))
    mt = open(os.path.join(body, 'motion.mtable'), 'rb').read()
    hashes = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    bmap = bone_map(open(os.path.join(vanilla_model, 'model.jtb'), 'rb').read(), os.path.join(vanilla_model, 'model.vbn'))
    g, e = clone_scripts(game, effect, hashes, bmap)
    ow = os.path.join(out_dir, 'weapon', 'clone')
    os.makedirs(ow, exist_ok=True)
    acmd.ACMDFile(g).save(os.path.join(ow, 'game.bin'))
    acmd.ACMDFile(e).save(os.path.join(ow, 'effect.bin'))
    if test_only:
        import omo as O
        names = [n for n, _p, _h in O.vbn_read(os.path.join(vanilla_model, 'model.vbn'))]
        import port_check
        t0, _t1 = port_check.jtb(open(os.path.join(vanilla_model, 'model.jtb'), 'rb').read())
        for tname, bone in CLONE_JOINT25_TESTS:
            bm2 = bone_map(open(os.path.join(vanilla_model, 'model.jtb'), 'rb').read(),
                           os.path.join(vanilla_model, 'model.vbn'), {25: bone})
            g2, e2 = clone_scripts(game, effect, hashes, bm2)
            td = os.path.join(test_only, tname, 'fighter', 'gekkouga', 'script', 'animcmd', 'weapon', 'clone')
            os.makedirs(td, exist_ok=True)
            acmd.ACMDFile(g2).save(os.path.join(td, 'game.bin'))
            acmd.ACMDFile(e2).save(os.path.join(td, 'effect.bin'))
    acmd.ACMDFile({}).save(os.path.join(ow, 'sound.bin'))
    open(os.path.join(ow, 'motion.mtable'), 'wb').write(mt)
    cmd_shuriken(user_dir, out_dir)          # ice detonation v1: the uncharged Water Shuriken's ice and sparkles
    return dict(scaled=n, tips=tips, game=len(g), effect=len(e), motions=len(hashes))


# ---------------------------------------------------------------- ice detonation v1: the uncharged Water Shuriken
# (the user: "make Greninja's uncharged Water Shuriken apply a weak ice effect. Also please add ice sparkles around uncharged
# Water Shuriken"). His shuriken's Shot (motion kind 8, script "Shot": Special_Hitbox IDs 0 (3 %) / 1 (11 %) and ATK_LERP
# 0 -> 1, the game lerping between them by the charge) is every shot short of the full charge (MaxShot, motion 0x10, is the
# full one: unchanged). Its sound script picks its small / big sound by Float_Var_Compare(5, <, 0.5): the shuriken's float
# 5, its charge (0 - 1). Uncharged = that float under SH_ICE_CHARGE (a tap): its game script's IDs 0 / 1 get Effect 4
# (ice) and the ice hit sound (SFXType 0x1C, their levels kept), the rest as they are; charged (a held shot) the vanilla hitboxes.
# Its effect script (empty in vanilla) gets the ice sparkles (his bank's PtcGekkougaIceSparkle, the common bank's frozen-
# fighter twinkles) on its joint 0 for its flight, under the same compare. Freezing needs knockback over 52.5 (the
# community sheet's Element tab): ID 0's KB (3 %, KBG 85, BKB 10) on a 100-weight fighter is 26 at 0 %% and reaches 52.5
# at about 89 %; under that the hit only shows the ice effect, over it a short freeze (12 x 3 % = 36 frames). The clones'
# shurikens are this article (clone articles v1): theirs follow. The ice element makes it a trigger for the ice detonation
SH_SHOT = 'Shot'
SH_ICE_CHARGE = 0.1
SH_ICE_HIT = dict(Effect=4, SFXType=0x1C)
ICE_SPARKLE = 0x3300024           # tools/gekkouga_fx.py PtcGekkougaIceSparkle (efc entry 0x24)


def var_compare(var, method, value):
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    return acmd.Command(by['Float_Var_Compare'], [var, method, value])


def block(name, words):
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    return acmd.Command(by[name], [words])


def words(cmds):
    return sum(1 + len(c.params) for c in cmds)


def shuriken_ice(game, effect):
    """the shuriken's Shot: uncharged (its float 5 < SH_ICE_CHARGE) ice hitboxes and sparkles, else as vanilla. game /
    effect: its ACMDFiles (changed in place)"""
    import acmd
    s = game.scripts[acmd.crc(SH_SHOT)]
    assert [c.name for c in s] == ['Special_Hitbox', 'Special_Hitbox', 'ATK_LERP', 'Script_End'], [c.name for c in s]
    van = [acmd.Command(c.ident, list(c.params)) for c in s[:3]]
    ice = [acmd.Command(c.ident, list(c.params)) for c in s[:3]]
    for c in ice[:2]:
        for k, v in SH_ICE_HIT.items():
            c.params[param(c, k)] = v
    els = block('Else', 2 + words(van))
    game.scripts[acmd.crc(SH_SHOT)] = [var_compare(5, 4, SH_ICE_CHARGE), block('True', 2 + words(ice) + 2)] + ice + \
        [els] + van + [s[3]]
    sp = [ext_graphic(ICE_SPARKLE, 0, 0.0, 0.0, 0.0, 1.0, 1)]
    assert not effect.scripts.get(acmd.crc(SH_SHOT))
    by = {v['name']: k for k, v in acmd.INFO.items()}
    effect.scripts[acmd.crc(SH_SHOT)] = [var_compare(5, 4, SH_ICE_CHARGE), block('True', 2 + words(sp))] + sp + \
        [acmd.Command(by['Script_End'], [])]
    return game, effect


def cmd_shuriken(user_dir, out_dir):
    """his shuriken's game / effect scripts (script/animcmd/weapon/shuriken) with the uncharged ice"""
    import acmd
    d = os.path.join(user_dir, 'weapon', 'shuriken')
    game = acmd.ACMDFile.load(os.path.join(d, 'game.bin'))
    effect = acmd.ACMDFile.load(os.path.join(d, 'effect.bin'))
    shuriken_ice(game, effect)
    o = os.path.join(out_dir, 'weapon', 'shuriken')
    os.makedirs(o, exist_ok=True)
    game.save(os.path.join(o, 'game.bin'))
    effect.save(os.path.join(o, 'effect.bin'))


# ---------------------------------------------------------------- the clone's model / motion
CLONE_MODEL_FILES = ('model.nud', 'model.nut', 'model.vbn', 'model.jtb', 'model.mta', 'model.xmb', 'model.nhb',
                     'model.sb', 'model.flp')   # bunshin's file set, from his body cNN (the costume's colours)
CLONE_FACE_FILES = ('material_anime_eye.pac', 'material_anime_eyelid.pac', 'material_anime_face.pac', 'model.moi')
# v2: his body cNN's face: the eye / eyelid / face material animations per motion (docs/params/fighter_files.md: the
# eyelid's are mesh visibility by mesh name, with model.moi's per-mesh info). Not his model.sbwl / model.ik (swing
# bone extras, leg IK: bunshin's set has neither)
CLONE_MOTION_PACS = ('main.pac', 'lhand.pac', 'rhand.pac', 'gekkougapt1.pac', 'gekkougapt2.pac', 'gekkougasw1.pac')
# v2: his body's motion parts too (the clone's motion info lists his parts: hands 3 / 4, parts 6 / 7 / 8)


# v9: the clone's motions are full-body, as bunshin's (its one motion animates every bone but the swing ones). A weapon
# plays only its main.pac motion: a bone none of it animates is never posed and its vertices draw at the stage's origin
# (the user's v8: "their tongues and parts of their model are attached to the origin of the stage"). Each main.pac
# motion gets his part motions' bones (same motion, the part's name in place of "Main"; resampled to main's frames, or
# the part's Wait1 when it has none), and the vertices on bones no motion animates (his helper / extra swing bones,
# posed only by his own fighter modules) move to their nearest animated ancestor: the same place the bone takes at its
# bind offset from that ancestor.
CLONE_PARTS = (('lhand.pac', 'Lhand'), ('rhand.pac', 'Rhand'), ('gekkougapt1.pac', 'Gekkougapt1'),
               ('gekkougapt2.pac', 'Gekkougapt2'), ('gekkougasw1.pac', 'Gekkougasw1'))
PART_FALLBACK = 'A00Wait1.omo'
# v9: no swing simulation on the clone: its model.sb keeps the header and lists no swing bones (as Cloud's, the empty
# file the Ultimate ports use). An article never steps the swing bones, so they stayed where they were first placed in
# the world (the user's v8 clip: the tongue on the floor under the jumping clones, the water streaks stretched back to
# where the clones had stood; D_parts' keyed sw1 didn't help); now the tongue (SWG_CMant0-8) is an ordinary bone chain
# keyed by his gekkougasw1 motions, and the other swing bones (no keys anywhere) are rebound to their parents.
# v9.1: v9 (empty model.sb + the merged main.pac) froze at the match load (the user's log: nothing after boot, not even
# the clones' set-up lines). The release goes back to his own model.sb and main.pac (v8's, loaded fine) and changes only
# the model.nud's bone indices: every vertex on a bone main.pac doesn't key (the parts' bones, the swing and helper
# bones) is moved to its nearest ancestor main.pac keys (CLONE_POSED = 'main'), so nothing hangs on a bone the article
# never poses (a rigid tongue, fingers and jaw in their rest pose). The merged motions / empty sb are TEST_ONLY.
CLONE_POSED = 'merged'
# v11 (the user's v10: the unswung model.sb made the tongue vanish): the release is v9.1's visible set with the merged
# motions (the tongue / jaw / fingers' vertices on main.pac's bones, his own model.sb); TEST_ONLY_DATA/sway is his own
# model.nud + model.sb for the E_sway exe (the clones' swing stepped natively)
CLONE_RELEASE = 'own'
# v15 (the user's v14 E_sway: "the clones have their own swing physics": the clone's model / motion object, MotionModule
# +0x10, has a swing system; the exe steps it): the release is his own model.nud (the tongue / water on their swing
# bones) with his own model.sb; 'rigid' (v11 - v14's: the vertices on main.pac's bones) is TEST_ONLY_DATA/rigid
# v10 (the user's v9.1: it loads, the merged main.pac too; the tongue / water stay on but rigid): the merged main.pac
# and his own model.nud again (vertices on their own bones; only helpers / the leg and water swing drops, which no
# motion keys, rebound), and his model.sb with the tongue's entries pointed at no bone (unswing_sb: same count and size,
# the parser skips them), so the tongue is keyed, not left in the world. 'main': v9.1's set.


def empty_sb(sb):
    """model.sb with no swing bones: its header (' BWS', version) and a count of 0"""
    assert sb[:4] == b' BWS', sb[:4]
    return sb[:8] + b'\0\0\0\0'


def full_motions(body_motion_dir, vbn_path):
    """his main.pac with every part's bones in each motion, the tracks in the model's bone order (vanilla's:
    tools/omo_sort.py): ([(name, omo bytes)], {main name: [parts from Wait1]})"""
    import omo as O
    order = {h: i for i, (_n, _p, h) in enumerate(O.vbn_read(vbn_path))}
    main = O.pac_read(os.path.join(body_motion_dir, 'main.pac'))
    parts = []
    for f, tok in CLONE_PARTS:
        d = dict(O.pac_read(os.path.join(body_motion_dir, f)))
        fb = [n for n in d if n.endswith(PART_FALLBACK)]
        assert len(fb) == 1, (f, fb)
        parts.append((tok, d, d[fb[0]]))
    out, fell = [], {}
    for name, data in main:
        m = O.Omo(data)
        have = {n[1] for n in m.nodes}
        for tok, d, fb in parts:
            pn = name.replace('Main', tok, 1)
            src = d.get(pn)
            if src is None:
                src = fb
                fell.setdefault(name, []).append(tok)
            po = O.Omo(src)
            for f_, h, c, keys in po.nodes:
                if h in have:
                    continue
                if m.frames:
                    idx = [min(len(keys) - 1, int(round(fr * (len(keys) - 1) / max(m.frames - 1, 1))))
                           for fr in range(m.frames)] if len(keys) != m.frames else list(range(m.frames))
                    m.nodes.append([f_, h, c, [keys[i] for i in idx]])
                else:
                    m.nodes.append([f_, h, c, []])
                have.add(h)
        m.nodes.sort(key=lambda nd: order.get(nd[1], len(order)))
        root_still(m, O.vbn_read(vbn_path)[0][2])
        out.append((name, m.encode()))
    return out, fell


def root_still(m, h):
    """clone fixes v2 (the user: the clones "clip back to a set position constantly" on the ground): his walks / runs /
    dash attack / dash grab move TransN forward (WalkMiddle 22 a loop, Run 33, AttackDash 25.5): a fighter's kinetics take
    that as his movement, an article draws it, so the clone's model ran ahead of its place (his X + its offset, which already
    has that movement) and snapped back at each loop. TransN's X / Z kept at 0 on every frame (Y and its rotation as they
    were); a motion whose TransN doesn't move sideways is left as it is"""
    import omo as O
    n = m.node(h)
    if n is None or not m.frames or 'pos' not in O.tracks(m, h):
        return False
    smp = [m.sample(h, fr) for fr in range(m.frames)]
    if all(abs(p[0]) < 1e-4 and abs(p[2]) < 1e-4 for p, _q, _s in smp):
        return False
    tr = O.tracks(m, h)
    O.set_node(m, h, pos=[(0.0, p[1], 0.0) for p, _q, _s in smp], rot=[q for _p, q, _s in smp] if 'rot' in tr else None,
               scl=[s_ for _p, _q, s_ in smp] if 'scl' in tr else None)
    return True


def rebind(nud, bones, posed):
    """a model.nud whose rigged vertices on bones not in posed (hashes) are on their nearest posed ancestor instead
    (bones: omo.vbn_read): (bytes, {bone name: the ancestor's})"""
    d = bytearray(nud)
    assert d[:4] == b'NDP3'
    _, _v, nmesh, _bs, _be, pstart, psize, vsize, vasize = struct.unpack('>IHhhhiiii', bytes(d[4:0x20]))
    poly_base = 0x30 + pstart
    va_base = poly_base + psize + vsize
    target = {}
    for i, (name, parent, h) in enumerate(bones):
        j = i
        while j >= 0 and bones[j][2] not in posed:
            j = bones[j][1] if 0 <= bones[j][1] < len(bones) else -1
        target[i] = j
    moved = {}
    for i in range(nmesh):
        o = 0x30 + i * 0x30
        npoly, obj = struct.unpack('>hi', bytes(d[o + 42:o + 48]))
        for j in range(npoly):
            q = obj + j * 0x30
            _po, _vo, vaoff, nv, vs, _us = struct.unpack('>iiiHBB', bytes(d[q:q + 16]))
            if vs >> 4 == 0:
                continue
            assert vs >> 4 == 4, 'bone type %d' % (vs >> 4)
            st = 12 + {0: 4, 1: 20, 3: 52, 6: 8, 7: 24}[vs & 0xF] + 8
            for k in range(nv):
                at = va_base + vaoff + k * st + st - 8
                for b in range(4):
                    bi, w = d[at + b], d[at + 4 + b]
                    if w and target.get(bi, bi) != bi:
                        assert target[bi] >= 0, bones[bi][0]
                        moved[bones[bi][0]] = bones[target[bi]][0]
                        d[at + b] = target[bi]
    return bytes(d), moved


def posed_bones(pac_entries):
    """the bone hashes any motion of a pac keys"""
    import omo as O
    return {nd[1] for _nm, data in pac_entries for nd in O.Omo(data).nodes}


def unswing_sb(sb, bones, keyed):
    """v10: model.sb with its entries for bones the motions key (keyed: hashes) pointed at no bone: the model library's
    swing parser (0x036B8040, version 0x10005: 0x8C-byte entries from +0xC, the bone hash first, little-endian) looks
    each entry's bone up (0x036B0318) and skips one it doesn't find (0x036B8474), and its second pass skips an entry
    never set up (byte +4 0); the count and size stay (v9's count 0 froze the load). -> (bytes, [bone names unswung])"""
    assert sb[:4] == b' BWS' and struct.unpack('<HH', sb[4:8]) == (5, 1), sb[:8]
    n = struct.unpack('<I', sb[8:12])[0]
    assert len(sb) == 12 + 0x8C * n, len(sb)
    names = {h: nm for nm, _p, h in bones}
    out, done = bytearray(sb), []
    for i in range(n):
        at = 12 + 0x8C * i
        h = struct.unpack('<I', sb[at:at + 4])[0]
        if h in keyed:
            g = (~h) & 0xFFFFFFFF
            assert g not in names and g != 0x0FFFFFFF
            struct.pack_into('<I', out, at, g)
            done.append(names.get(h, hex(h)))
    return bytes(out), done


def cmd_data(vanilla_fighter, out_fighter, test_only=None):
    """model/clone/c00-c07 (his body's, v2 with his face files), motion/clone/ (main.pac + his part pacs). v11
    (CLONE_RELEASE 'rigid'): main.pac = his motions with his parts' bones (merged), model.sb his own, model.nud with every
    vertex on a bone main.pac keys (v9.1's: the tongue / water visible and on the clone, rigid). test_only (a folder):
    sway/ = his own model.nud + model.sb (the tongue / water on their swing bones, for the E_sway exe)"""
    import shutil
    import omo as O
    n = 0
    body = os.path.join(vanilla_fighter, 'motion', 'body')
    motions, _fell = full_motions(body, os.path.join(vanilla_fighter, 'model', 'body', 'c00', 'model.vbn'))
    main_posed = posed_bones(O.pac_read(os.path.join(body, 'main.pac')))

    def to(kind, rel):
        t = os.path.join(test_only, kind, 'fighter', 'gekkouga', rel)
        os.makedirs(os.path.dirname(t), exist_ok=True)
        return t
    for c in range(8):
        src = os.path.join(vanilla_fighter, 'model', 'body', 'c%02d' % c)
        dst = os.path.join(out_fighter, 'model', 'clone', 'c%02d' % c)
        os.makedirs(dst, exist_ok=True)
        for f in CLONE_MODEL_FILES + CLONE_FACE_FILES:
            shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
            n += 1
        bones = O.vbn_read(os.path.join(src, 'model.vbn'))
        nud0 = open(os.path.join(src, 'model.nud'), 'rb').read()
        rigid = rebind(nud0, bones, main_posed)[0]
        open(os.path.join(dst, 'model.nud'), 'wb').write(nud0 if CLONE_RELEASE == 'own' else rigid)
        if test_only:
            rel = 'model/clone/c%02d/' % c
            shutil.copyfile(os.path.join(src, 'model.nud'), to('sway', rel + 'model.nud'))
            shutil.copyfile(os.path.join(src, 'model.sb'), to('sway', rel + 'model.sb'))
            open(to('rigid', rel + 'model.nud'), 'wb').write(rigid)   # v14 / v15: the rigid tongue (the fallback)
    dst = os.path.join(out_fighter, 'motion', 'clone')
    os.makedirs(dst, exist_ok=True)
    for f in CLONE_MOTION_PACS:
        shutil.copyfile(os.path.join(vanilla_fighter, 'motion', 'body', f), os.path.join(dst, f))
        n += 1
    O.pac_write(os.path.join(dst, 'main.pac'), motions)
    return n


# round gauge v1.1 package (the user: "please remove the invulnerability from the charge"): his vl group 1 entries of
# the stance motions (SpecialLw 0x271, SpecialAirLw 0x289; bytes 3 / 4: the motion's intangible window 8 - 19, set by the
# fighter update when the frame crosses 8, cleared when it crosses 19: the charge holds the motion at 14) zeroed
VL_EDITS = ('m0[625].3=0', 'm0[625].4=0', 'm0[649].3=0', 'm0[649].4=0')


def cmd_vl(vanilla_vl, out):
    """out/param/fighter/fighter_param_vl_gekkouga.bin: his vanilla vl with VL_EDITS"""
    o = os.path.join(out, 'param', 'fighter', 'fighter_param_vl_gekkouga.bin')
    os.makedirs(os.path.dirname(o), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(HERE, 'fighter_param_vl.py'), 'set', vanilla_vl, o, *VL_EDITS, '--kind',
                    'gekkouga'], check=True, stdout=subprocess.DEVNULL)
    return o


def cmd_all(vanilla_root, user_root, out):
    """the whole fighter/gekkouga of the package (+ fighter/kirby's MSC: the trait)"""
    import shutil
    vf = os.path.join(vanilla_root, 'fighter', 'gekkouga')
    of = os.path.join(out, 'fighter', 'gekkouga')
    info = cmd_acmd(os.path.join(user_root, 'fighter', 'gekkouga', 'script', 'animcmd'),
                    os.path.join(vf, 'model', 'body', 'c00'), os.path.join(of, 'script', 'animcmd'),
                    os.path.join(out, 'TEST_ONLY_DATA'))
    info['data_files'] = cmd_data(vf, of, os.path.join(out, 'TEST_ONLY_DATA'))   # v9.1: v9's data, to test
    msc = os.path.join(of, 'script', 'msc')
    os.makedirs(os.path.join(msc, 'clone'), exist_ok=True)
    compile_msc(os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), os.path.join(msc, 'gekkouga.mscsb'))
    compile_msc(CLONE_MSC, os.path.join(msc, 'clone', 'clone.mscsb'))
    os.makedirs(os.path.join(msc, 'shuriken'), exist_ok=True)   # clone articles v1: his shuriken (the clones' copies)
    compile_msc(SHURIKEN_MSC, os.path.join(msc, 'shuriken', 'shuriken.mscsb'))
    kirby = os.path.join(out, 'fighter', 'kirby', 'script', 'msc')
    os.makedirs(kirby, exist_ok=True)
    compile_msc(os.path.join(ROOT, 'fighters', 'kirby', 'kirby.c'), os.path.join(kirby, 'kirby.mscsb'))
    return info


# ---------------------------------------------------------------- skeleton v1: the Running Skeleton (article 8)
SKELETON_MSC = os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'skeleton.c')
SK_SCRIPTS = ('SkeletonRun', 'SkeletonExplode', 'SkeletonSmoke')   # its motion kinds 0 / 1 / 2 (motion.mtable)
SK_CARRIER = ('model.nud', 'model.nut', 'model.vbn', 'model.jtb', 'model.mta', 'model.xmb', 'model.nhb', 'model.sb',
              'model.flp')                # Pac-Man's hydrant's model (fighter/pacman/model/firehydrant/c00): its
                                          # joints and file set carry the article (hidden: the skeleton is an effect)
# its explosion (motion 1, frames 1 - 4): 15 %, 50 degrees, KBG 50 / BKB 40 (Smash 4's formula on Mario, weight 100:
# 130 % + 15 -> ((14.5 + 108.75) x 1.4 + 18) x 0.5 + 40 = 135 knockback, about a mid-stage KO; 0 % -> 58), flame,
# launched away from its middle (FacingRestrict 5), as the hydrant's hitboxes (bone 0, type 9, indirect)
SK_BOOM = dict(Damage=15.0, Angle=50, KBG=50, FKB=0, BKB=40, Size=27.0, Y=14.0, Effect=5, SFXLevel=2, SFXType=0xB,
               ShieldDamage=40)   # skeleton v1.5 (the user: "make the explosion effect and hitbox slightly bigger and do a lot
                                  # of shield damage"): size 22 -> 27 (x 1.23, its effect 44 -> 54 wide: tools/gekkouga_fx.py
                                  # SK_BOOM_DIAMETER); shield damage +40 on its 15 %: 55 against a fresh shield's 50 HP
                                  # (Smash 4: the hitbox's damage + its shield damage): a full shield breaks
SK_BOOM_FRAMES = 101               # skeleton v1.7 (the user: "make the explosion hitbox ... more active (until right before
                                   # all of the orange is gone in the explosion"); v1 - v1.6: 4): explosion_simple_24's orange
                                   # (tools/gekkouga_fx_test.py boom_orange: pixels R > 0.45, saturation > 0.35, R > B + 0.25,
                                   # alpha > 0.3, per cell; 4 game frames a cell) peaks in cells 14 - 16 (~4560 px), is 5 % of
                                   # that in cell 24, 2 % in 25 (frames 100 - 103), 1 % in 26, gone from 28 (frame 112): the
                                   # hitbox from its script's frame 0 (the effect's 1) to 101 (the effect's 102, inside cell
                                   # 25). One Extra_Special_Hitbox at the explode motion's frame 0, no WAIT / Remove: its motion
                                   # (the hydrant's: 30 / 48 frames) can't hold 101 frames and would loop (the script again: the
                                   # hitbox set again, a second hit); weapons/skeleton.c holds the motion (rate 0) the next frame
                                   # and turns the hitbox off (AttackModule 0x2719) at sk_boom_hit_frames() = this. Never set
                                   # again: its hit records hold, one hit an opponent
                                   # (Rehit 0) for the whole window. Its size stays 27 (the fireball's widest; a smaller one as
                                   # it fades would need Change_Hitbox_Size, whose effect on the records isn't known here)
SK_BOOM_HITSTUN = 1.6             # skeleton v1.5 (the user: "make the explosion have 1.6x hitstun"): Extra_Special_Hitbox's
                                  # HitstunMul (the ACMD extension's extras, tools/acmd_ext_cave.py: works in articles' scripts)
# skeleton v1.5's contact burn (the user: "about 4% overall but rehits quickly ... about 70% overall if it was for 1
# second"): while it runs (SkeletonRun), its body (tools/gekkouga_clone_cave.py SK_BODY: x +- 3.5, y 0 - 24) is a capsule
# hitbox (radius 3.5, Y 3.5 - 20.5 on joint 0) with no knockback, no hitlag, no flinch, 0.1 %, on 2 frames then off 1
# (Remove_All_Hitboxes: its hit log restarts, as vanilla up air's multi-hit): a touch every 3 frames; each hit's burn is
# the exe's contact row (SK_TOUCH_ROW: 3.5 %), 20 a second = 70 % (+ 2 % of the hits)
SK_TOUCH = dict(Damage=0.1, Angle=361, KBG=0, FKB=0, BKB=0, Size=3.5, Y=3.5, Y2=20.5, Effect=5, Hitlag=0.0, SDI=0.0,
                Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=0, SFXType=0, DisableHitlag=1, NoGFX=1, Flinchless=1)
SK_TOUCH_ON, SK_TOUCH_PERIOD = 2, 3     # (v1.5 / v1.6: on 2 frames, off 1; skeleton v1.7: TEST_ONLY_DATA skeleton_toggle)
SK_TOUCH_REHIT = 3                # skeleton v1.7 (the user: its multi-hit "seems inconsistent"): one hitbox for the whole
                                  # run with the game's rehit rate 3 (Hitbox.csv field 31: "how many frames need to play
                                  # before the hitbox can hit again"), set once a loop of its motion (48 frames, 16 periods);
                                  # the burns from every new hit record (the exe's feature mark: v1.5 / v1.6 counted records,
                                  # and a re-set's hit in the same frame as its clear went uncounted)


def sk_boom_hitbox():
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['Extra_Special_Hitbox']   # skeleton v1.5: + its hitstun x SK_BOOM_HITSTUN (v1 - v1.4: Special_Hitbox)
    syn = acmd.INFO[ident]['syntax']
    d = dict(ID=0, Part=0, Bone=0, Damage=0, Angle=0, KBG=0, FKB=0, BKB=0, Size=5, X=0, Y=0, Z=0, Effect=0, Trip=0,
             Hitlag=1.0, SDI=1.0, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=0, SFXType=0, Type=9, HitBits=0x3F,
             Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0,
             HitAllStates=0, FacingRestrict=5, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0,
             Shape=0)
    d['Ground/Air'] = 3
    d['Direct/Indirect'] = 0
    d.update(SK_BOOM)
    d.update(HitstunMul=SK_BOOM_HITSTUN, HitstopMul=0.0, HitstopFrames=0, SelfHitstopMul=0.0, SelfHitstopFrames=0, DIMul=0.0)
    return acmd.Command(ident, [d[n] for n in syn])


def sk_touch_hitbox():
    """skeleton v1.5: its body's contact hitbox (SK_TOUCH)"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['Extended_Special_Hitbox']
    syn = acmd.INFO[ident]['syntax']
    d = dict(ID=0, Part=0, Bone=0, X=0.0, Z=0.0, X2=0.0, Z2=0.0, Trip=0, Type=9, HitBits=0x3F, Unk41=0, CollisionPart=0xF,
             NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=0,
             NoGrabRelease=0, TeamDamage=0)
    d['Ground/Air'] = 3
    d['Direct/Indirect'] = 0
    d.update(SK_TOUCH)
    return acmd.Command(ident, [d[n] for n in syn])


def sk_run_script(frames=None, toggle=False):
    """SkeletonRun: skeleton v1.7: the contact hitbox once (rehit SK_TOUCH_REHIT); toggle (v1.5 / v1.6, TEST_ONLY): on
    SK_TOUCH_ON frames of every SK_TOUCH_PERIOD, through its motion (it loops: the script again from 0; its 30 / 48
    frames are whole periods)"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    if not toggle:
        c = sk_touch_hitbox()
        c.params[c.info['syntax'].index('Rehit')] = SK_TOUCH_REHIT
        return [c, acmd.Command(by['Script_End'], [])]
    frames = frames or 48
    out = []
    for f in range(0, frames, SK_TOUCH_PERIOD):
        if f:
            out.append(acmd.Command(by['FRAME'], [float(f)]))
        out.append(sk_touch_hitbox())
        out.append(acmd.Command(by['FRAME'], [float(f + SK_TOUCH_ON)]))
        out.append(acmd.Command(by['Remove_All_Hitboxes'], []))
    return out + [acmd.Command(by['Script_End'], [])]


def sk_scripts(toggle=False):
    """{crc: [Command]}: game (the explosion's hitbox), effect / sound empty"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    end = acmd.Command(by['Script_End'], [])
    boom = [sk_boom_hitbox(), end]        # skeleton v1.7: its MSC holds the motion and ends it (SK_BOOM_FRAMES)
    game = {acmd.crc(n): [acmd.Command(by['Script_End'], [])] for n in SK_SCRIPTS}
    game[acmd.crc('SkeletonExplode')] = boom
    game[acmd.crc('SkeletonRun')] = sk_run_script(toggle=toggle)
    return game


def sk_empty():
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    return {acmd.crc(n): [acmd.Command(by['Script_End'], [])] for n in SK_SCRIPTS}


def skeleton_lvd(hydrant_lvd):
    """its collision: the hydrant's .lvd (one collision, its flags / names kept) with the skeleton's lines: a wall each
    side and a floor on top (tools/gekkouga_clone_cave.py SK_VERTS: the executable moves these 4 vertices onto it)"""
    import lvd
    import gekkouga_clone_cave as C
    lv = lvd.LVD(hydrant_lvd)
    assert len(lv.collisions) == 1, 'the hydrant has one collision'
    c = lv.collisions[0]
    c.name, c.subname = 'COL_Skeleton', 'Skeleton'
    c.verts = [list(map(float, v)) for v in C.sk_verts(C.RELEASE)]   # (skeleton v1.5: its body's box)
    c.normals = [[-1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, -1.0]][:len(c.verts) - 1]   # left wall, top (a floor), right
    c.mats = [bytearray(c.mats[0]) for _ in range(len(c.verts) - 1)]   # wall, tuning v1 (skbot): its bottom (a ceiling,
    # right to left, 2 over its feet: the walls' foot): out of the solid. The collision isn't drop-through (flag 4 0)
    c.cliffs = []
    return lv.write()


def skeleton_lvd_floor(hydrant_lvd):
    """skeleton v1.1 (TEST_ONLY_DATA/skeleton_floor_only): the hydrant's .lvd as it is (one floor line, its 2 vertices,
    normal, material, flags) with only the line moved to the skeleton's top (SK_VERTS 1 / 2: x +- 6, y 28); the exe moves
    a 2-vertex ground's two onto those"""
    import lvd
    import gekkouga_clone_cave as C
    lv = lvd.LVD(hydrant_lvd)
    c = lv.collisions[0]
    assert len(c.verts) == 2
    c.verts = [list(map(float, v)) for v in C.sk_verts(C.RELEASE)[1:3]]
    return lv.write()


def cmd_skeleton(pacman_fighter, out_fighter, test_only=None):
    """the Running Skeleton's files: model/skeleton/c00 (the hydrant's model + skeleton.lvd), motion/skeleton/main.pac
    (the hydrant's: its motion info's hash), script/animcmd/weapon/skeleton, script/msc/skeleton/skeleton.mscsb"""
    import shutil
    import acmd
    src = os.path.join(pacman_fighter, 'model', 'firehydrant', 'c00')
    dst = os.path.join(out_fighter, 'model', 'skeleton', 'c00')
    os.makedirs(dst, exist_ok=True)
    for f in SK_CARRIER:
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
    open(os.path.join(dst, 'skeleton.lvd'), 'wb').write(skeleton_lvd(os.path.join(src, 'firehydrant.lvd')))
    if test_only:
        t = os.path.join(test_only, 'skeleton_floor_only', 'fighter', 'gekkouga', 'model', 'skeleton', 'c00')
        os.makedirs(t, exist_ok=True)
        open(os.path.join(t, 'skeleton.lvd'), 'wb').write(skeleton_lvd_floor(os.path.join(src, 'firehydrant.lvd')))
    md = os.path.join(out_fighter, 'motion', 'skeleton')
    os.makedirs(md, exist_ok=True)
    shutil.copyfile(os.path.join(pacman_fighter, 'motion', 'firehydrant', 'main.pac'), os.path.join(md, 'main.pac'))
    ow = os.path.join(out_fighter, 'script', 'animcmd', 'weapon', 'skeleton')
    os.makedirs(ow, exist_ok=True)
    acmd.ACMDFile(sk_scripts()).save(os.path.join(ow, 'game.bin'))
    if test_only:                         # skeleton v1.7: v1.5 / v1.6's toggled contact hitbox (with v1.7's explosion)
        t = os.path.join(test_only, 'skeleton_toggle', 'fighter', 'gekkouga', 'script', 'animcmd', 'weapon', 'skeleton')
        os.makedirs(t, exist_ok=True)
        acmd.ACMDFile(sk_scripts(toggle=True)).save(os.path.join(t, 'game.bin'))
    acmd.ACMDFile(sk_empty()).save(os.path.join(ow, 'effect.bin'))
    acmd.ACMDFile(sk_empty()).save(os.path.join(ow, 'sound.bin'))
    open(os.path.join(ow, 'motion.mtable'), 'wb').write(b''.join(struct.pack('>I', acmd.crc(n)) for n in SK_SCRIPTS))
    ms = os.path.join(out_fighter, 'script', 'msc', 'skeleton')
    os.makedirs(ms, exist_ok=True)
    compile_msc(SKELETON_MSC, os.path.join(ms, 'skeleton.mscsb'))
    return len(SK_CARRIER) + 6



SND_TEST_AT = '    WorkModule(0, (float)r + 0, 0x0f000317);   // diag: the generate\'s result (the TEST_ONLY exe logs it: S4GF gen=)\n'
SND_TEST = ('    WorkModule(0, (float)SoundModule(0x2710, 0x768005b) + 0, 0x0f000317); // skeleton v1.7 TEST_ONLY: its spawn '
            'sound from him (his SoundModule), the answer in VAR_23 (S4GF gen=)\n')


def sound_test_msc(src):
    """skeleton v1.7 TEST_ONLY_DATA sound_via_greninja: his MSC source with the skeleton's first spawn sound (0x0768005B)
    also played by him as he asks for a skeleton (gk_sk_spawn): it plays -> the bank / table are right"""
    a, b, c = func_span(src, 'gk_sk_spawn')
    body = src[b:c]
    assert body.count(SND_TEST_AT) == 1
    return src[:b] + body.replace(SND_TEST_AT, SND_TEST_AT + SND_TEST) + src[c:]


# ---------------------------------------------------------------- burn v2: the smashes' fire trails (article 9)
TRAIL_MSC = os.path.join(ROOT, 'fighters', 'gekkouga', 'weapons', 'firetrail.c')
TR_SCRIPTS = ('FireTrailS4', 'FireTrailHi4', 'FireTrailLw4', 'FireTrailIceBoom')   # its motion kinds 0 / 1 / 2 (forward /
# up / down smash); ice detonation v1: 3, the blast (no hitbox in its script: weapons/firetrail.c ib_start makes it, its
# damage and size from the burn amount)
# its hitboxes (bone 0, held from the motion's first frame): along each smash's path, where its fire is (firetrail.c
# tr_fx_*): (Z forward along its way, Y up, size). No knockback (KBG / FKB / BKB 0), no hitlag, no flinch, no hit effect,
# 0.1 % (a hit to log: the burn is the exe's trail row, 0.25 % every 15 frames for 3 s = 3 %), re-hit every TR_REHIT
TR_BOXES_V1 = {'FireTrailS4': ((14.0, 5.0, 7.0), (26.0, 5.0, 7.0), (38.0, 5.0, 7.0)),
               'FireTrailHi4': ((6.0, 5.0, 7.0), (-6.0, 5.0, 7.0), (14.0, 5.0, 7.0), (-14.0, 5.0, 7.0)),   # skeleton v1.4:
                                                                       # on its flames under it (v1 - fire trail fix v1: a column)
               'FireTrailLw4': ((14.0, 5.0, 8.0), (30.0, 5.0, 8.0), (-14.0, 5.0, 8.0), (-30.0, 5.0, 8.0))}
# tuning v1 (the user: "please make the trail fire more full, for each smash attack and match them better"): the denser
# flames (firetrail.c tr_fx_*: forward 12 from 8 to 85 along the longer forward smash, down 8 each side 6 - 55 along its
# sweep, up 4 each side 4 - 22 under its geyser) covered end to end
TR_BOXES = {'FireTrailS4': tuple((12.0 + 12.0 * i, 5.0, 7.0) for i in range(7)),
            'FireTrailHi4': tuple((sg * z, 5.0, 7.0) for z in (6.0, 15.0, 22.0) for sg in (1.0, -1.0)),
            'FireTrailLw4': tuple((sg * z, 5.0, 8.0) for z in (12.0, 26.0, 40.0, 52.0) for sg in (1.0, -1.0))}
TR_REHIT = 35
TR_HIT = dict(Damage=0.1, Angle=361, KBG=0, FKB=0, BKB=0, Effect=5, Hitlag=0.0, SDI=0.0, Clang=0, Rebound=0,
              ShieldDamage=0, SFXLevel=0, SFXType=0, Rehit=TR_REHIT, DisableHitlag=1, NoGFX=1, Flinchless=1,
              Type=0x16)
# smash tune v1: Type 0x16 (Water: no Smash 4 hitbox uses it, the community sheet's Type tab; burn v2 - nair / fair v1: 9,
# Weapon) marks the trail's hitboxes for the executable's shield damage halving (tools/gekkouga_clone_cave.py feature
# shalf: a Greninja's attack with this Type at its attack data +0x55, as his and the clones' smash motions: x 0.5). They
# draw nothing (NoGFX) and make no sound, which is where a hitbox's Type could show


def tr_hitbox(i, z, y, size):
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['Special_Hitbox']
    syn = acmd.INFO[ident]['syntax']
    d = dict(ID=i, Part=0, Bone=0, Damage=0, Angle=0, KBG=0, FKB=0, BKB=0, Size=size, X=0, Y=y, Z=z, Effect=0, Trip=0,
             Hitlag=1.0, SDI=1.0, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=0, SFXType=0, Type=9, HitBits=0x3F,
             Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0,
             HitAllStates=0, FacingRestrict=0, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0,
             Shape=0)
    d['Ground/Air'] = 3
    d['Direct/Indirect'] = 0
    d.update(TR_HIT)
    return acmd.Command(ident, [d[n] for n in syn])


def tr_scripts():
    """{crc: [Command]}: each smash's hitboxes at once (its MSC holds the motion at frame 0), then the end"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    return {acmd.crc(n): [tr_hitbox(i, *b) for i, b in enumerate(TR_BOXES.get(n, ()))] + [acmd.Command(by['Script_End'], [])]
            for n in TR_SCRIPTS}


def tr_empty():
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    return {acmd.crc(n): [acmd.Command(by['Script_End'], [])] for n in TR_SCRIPTS}


def cmd_trail(pacman_fighter, out_fighter):
    """the fire trail's files: model/firetrail/c00 (the hydrant's model: a hidden carrier), motion/firetrail/main.pac
    (the hydrant's), script/animcmd/weapon/firetrail, script/msc/firetrail/firetrail.mscsb"""
    import shutil
    import acmd
    src = os.path.join(pacman_fighter, 'model', 'firehydrant', 'c00')
    dst = os.path.join(out_fighter, 'model', 'firetrail', 'c00')
    os.makedirs(dst, exist_ok=True)
    for f in SK_CARRIER:
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
    md = os.path.join(out_fighter, 'motion', 'firetrail')
    os.makedirs(md, exist_ok=True)
    shutil.copyfile(os.path.join(pacman_fighter, 'motion', 'firehydrant', 'main.pac'), os.path.join(md, 'main.pac'))
    ow = os.path.join(out_fighter, 'script', 'animcmd', 'weapon', 'firetrail')
    os.makedirs(ow, exist_ok=True)
    acmd.ACMDFile(tr_scripts()).save(os.path.join(ow, 'game.bin'))
    acmd.ACMDFile(tr_empty()).save(os.path.join(ow, 'effect.bin'))
    acmd.ACMDFile(tr_empty()).save(os.path.join(ow, 'sound.bin'))
    open(os.path.join(ow, 'motion.mtable'), 'wb').write(b''.join(struct.pack('>I', acmd.crc(n)) for n in TR_SCRIPTS))
    ms = os.path.join(out_fighter, 'script', 'msc', 'firetrail')
    os.makedirs(ms, exist_ok=True)
    compile_msc(TRAIL_MSC, os.path.join(ms, 'firetrail.mscsb'))
    return len(SK_CARRIER) + 6

if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == 'msc':
        cmd_msc(a[1], a[2])
    elif len(a) == 4 and a[0] == 'acmd':
        print(cmd_acmd(a[1], a[2], a[3]))
    elif len(a) == 3 and a[0] == 'data':
        print(cmd_data(a[1], a[2]))
    elif len(a) == 4 and a[0] == 'all':
        print(cmd_all(a[1], a[2], a[3]))
    elif len([x for x in a if not x.startswith('--common=')]) in (5, 6) and a[0] == 'effects':
        import gekkouga_fx                   # (a 6th argument --skeleton-only: skeleton v1.2's bank, without burn v2's;
        cm = next((x[9:] for x in a if x.startswith('--common=')), None)   # ice detonation v1: --common=common.010d0000.ptcl
        a = [x for x in a if not x.startswith('--common=')]
        for k, v in gekkouga_fx.build(a[1], a[2], a[3], os.path.join(a[4], 'effect', 'gekkouga'),
                                      burn2=a[5:] != ['--skeleton-only'], common=cm).items():
            print('0x%08X %s' % (v, k))
    elif len(a) == 3 and a[0] == 'trail':
        print(cmd_trail(a[1], a[2]))
    elif len(a) == 3 and a[0] == 'vl':
        print(cmd_vl(a[1], a[2]))
    elif len(a) in (3, 4) and a[0] == 'skeleton':
        print(cmd_skeleton(a[1], a[2], a[3] if len(a) > 3 else None))
    else:
        sys.exit(__doc__)
