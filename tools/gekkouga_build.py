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


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'msc':
        cmd_msc(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
