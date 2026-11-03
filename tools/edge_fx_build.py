#!/usr/bin/env python3
"""Sephiroth's effect bank (test 60): his edge_* effects, the turned variants his scripts call, and Ultimate's own
common sys_* sets (from ef_common.eff, tinted as his scripts tint them), so none of his moves fall back to Smash 4's
common effects (the user, test 59: "he still seems to use some of the old fixes for effects (jabs, dash attack, etc)").

  python3 tools/edge_fx_build.py EF_EDGE_EFF ZELDA_EFFECT_DIR EF_COMMON_EFF LUA2CPP_EDGE VANILLA_FIGHTER_DIR OUT \
      [--variants VARIANTS.json] [--ids fighters/edge/edge_effects.json]

EF_EDGE_EFF: Ultimate's fighter/edge/effect/ef_edge.eff; ZELDA_EFFECT_DIR: Smash 4's fighter/zelda/effect/zelda (the
bank it replaces); EF_COMMON_EFF: Ultimate's effect/system/common/ef_common.eff; LUA2CPP_EDGE: the lua2cpp dump
(edge/, edge_fire/...); VANILLA_FIGHTER_DIR: Smash 4's fighter/ (templates: */effect/*/*.ptcl). Writes OUT/ids.json
and the ptcl / efc (named zelda.010d0000.*: ship as edge.010d0000.*); copy OUT/ids.json back to edge_effects.json
and re-run tools/edge_specials_build.py so the scripts take the new ids (fighters/edge/README.md test 60).

The common sets: every sys_* name his Ultimate scripts use, plus SMASH4_SYS (Smash 4 common effects the script
translator maps back to an Ultimate name: reference/ultimate_sys_effects.json), each with a set in ef_common.eff
(ultimate_port.common_sets). Names without one (sys_screw, sys_bomb_a) stay Smash 4's (port_check E3 lists them).
The ids: --ids keeps every id it has (new names after them), so a rebuild doesn't move his calls.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ultimate_port  # noqa: E402
import ultimate_tints  # noqa: E402

# Smash 4 common effects in his kept scripts (Zelda's / the universal mechanics') whose Ultimate name has a set
SMASH4_SYS = ('sys_spin_wind', 'sys_damage_fire', 'sys_whirlwind_l', 'sys_flash')


def script_sys_names(lua2cpp):
    names = set()
    for f in glob.glob(os.path.join(lua2cpp, '*', '*.txt')):
        names |= set(re.findall(r'Hash40::new\("(sys_\w+)"\)', open(f, errors='replace').read()))
    return names


def main():
    ap = argparse.ArgumentParser()
    for a in ('eff', 'zelda_effect', 'ef_common', 'lua2cpp', 'vanilla_fighter', 'out'):
        ap.add_argument(a)
    ap.add_argument('--variants')
    ap.add_argument('--ids', default=os.path.join(HERE, '..', 'fighters', 'edge', 'edge_effects.json'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = json.load(open(a.ids))
    ids_out = os.path.join(a.out, 'ids.json')
    json.dump(ids, open(ids_out, 'w'), indent=1)
    effs = sorted((k for k in ids if k.startswith('edge_') and '@' not in k), key=lambda k: int(ids[k], 0))
    sets = ultimate_port.common_sets(sorted(script_sys_names(a.lua2cpp) | set(SMASH4_SYS)), a.ef_common)
    extra = ['%s=%s' % kv for kv in sorted(sets.items()) if kv[1]]
    print('common sets: %d (%s); none: %s' % (len(extra), ', '.join(sorted(k for k, v in sets.items() if v)),
                                              ', '.join(sorted(k for k, v in sets.items() if not v)) or '-'))
    cmd = [sys.executable, os.path.join(HERE, 'vfxb_to_ptcl.py'), a.eff, a.zelda_effect, a.out, '0x42', ids_out] + effs
    cmd += ['--templates'] + sorted(glob.glob(os.path.join(a.vanilla_fighter, '*', 'effect', '*', '*.ptcl')))
    if a.variants:
        cmd += ['--variants', a.variants]
    cmd += ['--extra-eff', a.ef_common] + extra + ultimate_tints.tint_args('edge', a.lua2cpp, None)
    sys.exit(subprocess.call(cmd))


if __name__ == '__main__':
    main()
