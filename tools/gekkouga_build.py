#!/usr/bin/env python3
"""Greninja's clones / smash charges mod (fighters/gekkouga/README.md "Clones v1"): builds every file of it.

  python3 tools/gekkouga_build.py msc VANILLA.c OUT.c          the MSC source: universal mechanics + this mod
  python3 tools/gekkouga_build.py acmd USER_ANIMCMD_DIR OUT_DIR the body scripts (smash growth) + the clone's
  python3 tools/gekkouga_build.py data VANILLA_FIGHTER_DIR OUT  the clone's model (c00-c07) / motion folders
  python3 tools/gekkouga_build.py all VANILLA_ROOT USER_ROOT OUT (VANILLA_ROOT/fighter/gekkouga, USER_ROOT/fighter/
                                                                gekkouga/script/animcmd) -> OUT/fighter/gekkouga/...

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
GROW = 1.5                 # clones.c gk_smash_grow(): every smash is a full charge, so its hitboxes / effects are x1.5
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
    """his smash scripts: hitbox sizes x GROW (game), effect sizes x GROW (effect)"""
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
                    c.params[k] = round(float(c.params[k]) * GROW, 4)
                    n += 1
    return n


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


def cmd_data(vanilla_fighter, out_fighter):
    """model/clone/c00-c07 (his body's), motion/clone/main.pac (his body's: every motion the clone plays)"""
    import shutil
    n = 0
    for c in range(8):
        src = os.path.join(vanilla_fighter, 'model', 'body', 'c%02d' % c)
        dst = os.path.join(out_fighter, 'model', 'clone', 'c%02d' % c)
        os.makedirs(dst, exist_ok=True)
        for f in CLONE_MODEL_FILES:
            shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
            n += 1
    dst = os.path.join(out_fighter, 'motion', 'clone')
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(os.path.join(vanilla_fighter, 'motion', 'body', 'main.pac'), os.path.join(dst, 'main.pac'))
    return n + 1


def cmd_all(vanilla_root, user_root, out):
    """the whole fighter/gekkouga of the package (+ fighter/kirby's MSC: the trait)"""
    import shutil
    vf = os.path.join(vanilla_root, 'fighter', 'gekkouga')
    of = os.path.join(out, 'fighter', 'gekkouga')
    info = cmd_acmd(os.path.join(user_root, 'fighter', 'gekkouga', 'script', 'animcmd'),
                    os.path.join(vf, 'model', 'body', 'c00'), os.path.join(of, 'script', 'animcmd'))
    info['data_files'] = cmd_data(vf, of)
    msc = os.path.join(of, 'script', 'msc')
    os.makedirs(os.path.join(msc, 'clone'), exist_ok=True)
    compile_msc(os.path.join(ROOT, 'fighters', 'gekkouga', 'gekkouga.c'), os.path.join(msc, 'gekkouga.mscsb'))
    compile_msc(CLONE_MSC, os.path.join(msc, 'clone', 'clone.mscsb'))
    kirby = os.path.join(out, 'fighter', 'kirby', 'script', 'msc')
    os.makedirs(kirby, exist_ok=True)
    compile_msc(os.path.join(ROOT, 'fighters', 'kirby', 'kirby.c'), os.path.join(kirby, 'kirby.mscsb'))
    return info


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
    else:
        sys.exit(__doc__)
