#!/usr/bin/env python3
"""Greninja's clones / smash charges mod (fighters/gekkouga/README.md "Clones v1"): builds every file of it.

  python3 tools/gekkouga_build.py msc VANILLA.c OUT.c          the MSC source: universal mechanics + this mod
  python3 tools/gekkouga_build.py acmd USER_ANIMCMD_DIR OUT_DIR the body scripts (smash growth) + the clone's
  python3 tools/gekkouga_build.py data VANILLA_FIGHTER_DIR OUT  the clone's model (c00-c07) / motion folders
  python3 tools/gekkouga_build.py all VANILLA_ROOT USER_ROOT OUT (VANILLA_ROOT/fighter/gekkouga, USER_ROOT/fighter/
                                                                gekkouga/script/animcmd) -> OUT/fighter/gekkouga/...
  python3 tools/gekkouga_build.py skeleton PACMAN_FIGHTER_DIR OUT_FIGHTER [TEST_ONLY_DIR]   skeleton v1: its files
                                                                (vanilla fighter/pacman: its hydrant's model / motion)
  python3 tools/gekkouga_build.py effects VANILLA_EFFECT_DIR KIRBY_PTCL FX_PKG OUT_FIGHTER   skeleton v1.2 on: his
                                                                effect bank + the flipbooks (tools/gekkouga_fx.py) ->
                                                                OUT_FIGHTER/effect/gekkouga/gekkouga.010d0000.ptcl / .efc

VANILLA.c: the decompiled vanilla MSC with its labels (git show 0932c7b:fighters/gekkouga/gekkouga.c); the result is
fighters/gekkouga/gekkouga.c. The MSC step runs tools/universal_mechanics.py on it (roll-off 2.2 / 1.0, Hero's
momentum, reverse tilts, tilts / down smash / shield out of run: the user's rolloff_hero_v1 gekkouga.mscsb compiles
to the same functions, msc_fingerprint 0 differ), then patches the sites below and appends fighters/gekkouga/clones.c.
The clone article's MSC is fighters/gekkouga/weapons/clone.c (compiled as it is).
"""
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
}
# attack loops: a chain cancel first
MSC_CHAIN = {'func_293': 0x1, 'func_302': 0x2, 'func_309': 0x4}


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
    return src + '\n' + open(CLONES_C).read()


def cmd_msc(vanilla, out):
    tmp = out + '.um.c'
    subprocess.run([sys.executable, os.path.join(HERE, 'universal_mechanics.py'), '--name', 'gekkouga', vanilla, tmp],
                   check=True, stdout=subprocess.DEVNULL)
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
CHARGE_DAMAGE = 1.4        # Smash 4's full smash charge (the attack's 0x1000000 ratio 1.0): x1.4 damage. The clones'
                           # copies of his smash hitboxes get it in the script (an article's attack has no charge ratio)
HITBOXES = ('Hitbox', 'Special_Hitbox', 'Extended_Hitbox', 'Extended_Special_Hitbox')
CLONE_GAME = set(HITBOXES) | {'FRAME', 'WAIT', 'Remove_All_Hitboxes', 'Remove_Hitbox', 'Move_Hitbox', 'Script_End'}
CLONE_EFFECT = {'FRAME', 'WAIT', 'Script_End', 'Graphic_Effect2', 'External_Graphic', 'EFFECT_FLIP', 'EFFECT_FOLLOW_FLIP',
                'Terminate_Graphic_Effect', 'Sword_Glow', 'Terminate_Sword_Glow'}
FLOW = {'Set_Loop', 'Goto', 'Float_Var_Compare', 'True', 'Else', 'False', 'IS_FLAG', 'CALL', 'JUMP', 'EXECUTE',
        'Loop_Rest', 'Float_Compare', 'WAIT_LOOP_CLR'}
NO_CLONE = {'IS_FLAG', 'CALL', 'JUMP'}     # scripts using these (his counter's attacks, ...) aren't copied
FLOW_KEEP_SAFE = {'SET_FLOAT'}             # kept inside a loop / condition (position variables only: from an article
                                           # they find nobody), never anything else
FINAL_FIRST = 0x295                        # his Final Smash's motions (0x295 - 0x29B): not copied (the clones idle then)
WEAPON_JOINT = 0x7D0                       # an article's joint = 0x7D0 + its model.jtb table-0 entry


def param(c, name):
    return c.info['syntax'].index(name)


def bone_map(jtb_bytes, vbn_path):
    """his body joint id (table 0 below 1000, table 1 from 1000) -> the clone article's (0x7D0 + table-0 entry):
    a bone missing from table 0 goes to its nearest ancestor that is there"""
    import port_check
    import omo
    t0, t1 = port_check.jtb(jtb_bytes)
    bones = omo.vbn_read(vbn_path)
    where = {b: n for n, b in enumerate(t0)}

    def m(j):
        if j == 0:
            return 0
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
                if 'Size' in syn and (c.name in HITBOXES or f is effect):
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


def clone_scripts(game, effect, mtable_hashes, bmap):
    """the clone article's game / effect scripts: his body's hitbox scripts (bones remapped, his smashes' damage x
    CHARGE_DAMAGE) and their effects (EFFECT / follow / flip / trails only); {crc: [Command]} each"""
    import acmd
    smash = {zlib.crc32(n.encode()) for n in SMASH_SCRIPTS}
    g_out, e_out = {}, {}
    final = {h for i, h in enumerate(mtable_hashes) if i >= FINAL_FIRST}
    for crc in sorted(set(mtable_hashes) - final):
        s = game.scripts.get(crc)
        if not s or not any(c.name in HITBOXES for c in s) or any(c.name in NO_CLONE for c in s):
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
        e = effect.scripts.get(crc)
        if e and crc in smash:
            e = flatten(e)                # v4: his smashes' effects too (their conditions: the True branches)
        if e and not any(c.name in FLOW for c in e):
            eo = []
            for c in e:
                if c.name not in CLONE_EFFECT:
                    continue
                c2 = acmd.Command(c.ident, list(c.params))
                for nm in ('Bone', 'Bone1', 'Bone2', 'Bone3'):
                    if nm in c2.info['syntax']:
                        k = param(c2, nm)
                        c2.params[k] = bmap(int(c2.params[k]))
                eo.append(c2)
            if any(c.name not in ('FRAME', 'WAIT', 'Script_End') for c in eo):
                e_out[crc] = eo
    return g_out, e_out


def cmd_acmd(user_dir, vanilla_model, out_dir):
    """user_dir: his script/animcmd (body/ game, effect, sound, expression, motion.mtable); vanilla_model: his
    model/body/c00 (model.jtb / model.vbn for the clone's joints); out_dir: script/animcmd of the package"""
    import acmd
    body = os.path.join(user_dir, 'body')
    game = acmd.ACMDFile.load(os.path.join(body, 'game.bin'))
    effect = acmd.ACMDFile.load(os.path.join(body, 'effect.bin'))
    n = scale_smash(game, effect)
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
    acmd.ACMDFile({}).save(os.path.join(ow, 'sound.bin'))
    open(os.path.join(ow, 'motion.mtable'), 'wb').write(mt)
    return dict(scaled=n, game=len(g), effect=len(e), motions=len(hashes))


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
        out.append((name, m.encode()))
    return out, fell


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


def cmd_all(vanilla_root, user_root, out):
    """the whole fighter/gekkouga of the package (+ fighter/kirby's MSC: the trait)"""
    import shutil
    vf = os.path.join(vanilla_root, 'fighter', 'gekkouga')
    of = os.path.join(out, 'fighter', 'gekkouga')
    info = cmd_acmd(os.path.join(user_root, 'fighter', 'gekkouga', 'script', 'animcmd'),
                    os.path.join(vf, 'model', 'body', 'c00'), os.path.join(of, 'script', 'animcmd'))
    info['data_files'] = cmd_data(vf, of, os.path.join(out, 'TEST_ONLY_DATA'))   # v9.1: v9's data, to test
    msc = os.path.join(of, 'script', 'msc')
    os.makedirs(os.path.join(msc, 'clone'), exist_ok=True)
    compile_msc(os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), os.path.join(msc, 'gekkouga.mscsb'))
    compile_msc(CLONE_MSC, os.path.join(msc, 'clone', 'clone.mscsb'))
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
SK_BOOM = dict(Damage=15.0, Angle=50, KBG=50, FKB=0, BKB=40, Size=22.0, Y=14.0, Effect=5, SFXLevel=2, SFXType=0xB)
SK_BOOM_FRAMES = 4


def sk_boom_hitbox():
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    ident = by['Special_Hitbox']
    syn = acmd.INFO[ident]['syntax']
    d = dict(ID=0, Part=0, Bone=0, Damage=0, Angle=0, KBG=0, FKB=0, BKB=0, Size=5, X=0, Y=0, Z=0, Effect=0, Trip=0,
             Hitlag=1.0, SDI=1.0, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=0, SFXType=0, Type=9, HitBits=0x3F,
             Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0,
             HitAllStates=0, FacingRestrict=5, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0,
             Shape=0)
    d['Ground/Air'] = 3
    d['Direct/Indirect'] = 0
    d.update(SK_BOOM)
    return acmd.Command(ident, [d[n] for n in syn])


def sk_scripts():
    """{crc: [Command]}: game (the explosion's hitbox), effect / sound empty"""
    import acmd
    by = {v['name']: k for k, v in acmd.INFO.items()}
    end = acmd.Command(by['Script_End'], [])
    boom = [sk_boom_hitbox(), acmd.Command(by['WAIT'], [float(SK_BOOM_FRAMES)]),
            acmd.Command(by['Remove_All_Hitboxes'], []), end]
    game = {acmd.crc(n): [acmd.Command(by['Script_End'], [])] for n in SK_SCRIPTS}
    game[acmd.crc('SkeletonExplode')] = boom
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
    c.verts = [list(map(float, v)) for v in C.SK_VERTS]
    c.normals = [[-1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]          # left wall, top (a floor), right wall: out of the solid
    c.mats = [bytearray(c.mats[0]) for _ in range(3)]
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
    c.verts = [list(map(float, v)) for v in C.SK_VERTS[1:3]]
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
    acmd.ACMDFile(sk_empty()).save(os.path.join(ow, 'effect.bin'))
    acmd.ACMDFile(sk_empty()).save(os.path.join(ow, 'sound.bin'))
    open(os.path.join(ow, 'motion.mtable'), 'wb').write(b''.join(struct.pack('>I', acmd.crc(n)) for n in SK_SCRIPTS))
    ms = os.path.join(out_fighter, 'script', 'msc', 'skeleton')
    os.makedirs(ms, exist_ok=True)
    compile_msc(SKELETON_MSC, os.path.join(ms, 'skeleton.mscsb'))
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
    elif len(a) in (5, 6) and a[0] == 'effects':
        import gekkouga_fx                   # (a 6th argument --skeleton-only: skeleton v1.2's bank, without burn v2's)
        for k, v in gekkouga_fx.build(a[1], a[2], a[3], os.path.join(a[4], 'effect', 'gekkouga'),
                                      burn2=a[5:] != ['--skeleton-only']).items():
            print('0x%08X %s' % (v, k))
    elif len(a) in (3, 4) and a[0] == 'skeleton':
        print(cmd_skeleton(a[1], a[2], a[3] if len(a) > 3 else None))
    else:
        sys.exit(__doc__)
