#!/usr/bin/env python3
"""The colours Ultimate's engine and a fighter's effect scripts put on effects, for a port's effect bank
and its translated scripts (tools/ultimate_port.py, tools/ultimate_acmd.py).

- The fighter's tint: Ultimate's FighterEffectModule::init (ExeFS 0x6C9280) maps the six names below to
  fighter_param_table[kind].common_effect_0_r / _g / _b (fighter_param.prc), and every request of one of them
  sets that colour on the effect (vt+0x4B8 0x6C9A40 -> the LAST_EFFECT_SET_COLOR setter 0x3563F40): eft2
  multiplies the emitters' colours by it, linear. Squirtle (0.32, 1.6, 0.4) green: his jabs, tilts and
  aerials' arcs and lines drew white without it (effects test 24). A later LAST_EFFECT_SET_COLOR replaces it.
  docs/ultimate-fighter-port.md "Effects recoloured at run time".
- Script colours: LAST_PARTICLE_SET_COLOR (ExeFS 0x22A5940 -> EffectModule vt+0x300: the last effect record's
  +0x160) after an effect. When every call of an effect in the fighter's scripts is followed by the same
  colour, it is baked into the bank's copy (exact, whatever Smash 4's command of the same name does with a
  universal-path program); the translator then drops the command after it.

  python3 tools/ultimate_tints.py ULT [SCRIPTS_DIR]       print them
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TINTED = ('sys_attack_line', 'sys_attack_line_b', 'sys_attack_arc', 'sys_attack_arc_b', 'sys_attack_arc_c',
          'sys_attack_arc_d')

_CALL = re.compile(r'macros::(\w+)\(agent, Hash40::new\("([^"]+)"\)')
_COLOUR = re.compile(r'macros::LAST_PARTICLE_SET_COLOR\(agent, ([^)]*)\)')


def fighter_tint(ult):
    """(r, g, b) from fighter_param.prc's common_effect_0 (None when the param or the fighter isn't found)"""
    import port_sources
    import ultimate_stats
    src = port_sources.load()
    prc = src.find('ult_common', 'param/fighter_param.prc')
    if not prc or not src.get('labels'):
        return None
    e = ultimate_stats.entry(prc, src['labels'], ult)
    v = tuple(float(e.get('common_effect_0_' + c, 1.0)) for c in 'rgb')
    return v


def script_colours(scripts_dir):
    """{effect: (r, g, b)} for the effects every one of whose calls is followed by the same LAST_PARTICLE_SET_COLOR"""
    seen = {}
    for path in sorted(os.listdir(scripts_dir)) if scripts_dir and os.path.isdir(scripts_dir) else []:
        if not path.endswith('.txt'):
            continue
        last = None
        for line in open(os.path.join(scripts_dir, path)):
            m = _CALL.search(line)
            if m and ('EFFECT' in m.group(1)):
                if last is not None:
                    seen.setdefault(last, set()).add(None)     # the previous call set none
                last = m.group(2)
                continue
            m = _COLOUR.search(line)
            if m and last is not None:
                seen.setdefault(last, set()).add(tuple(round(float(v.split(' as ')[0]), 4) for v in m.group(1).split(',')))
                last = None
            elif re.search(r'\bfn \w+\(', line) and last is not None:
                seen.setdefault(last, set()).add(None)
                last = None
        if last is not None:
            seen.setdefault(last, set()).add(None)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1 and None not in v}


def tints(ult, scripts_dir=None):
    """{effect: (r, g, b)} linear: the fighter's tint on TINTED, times the uniform script colours"""
    out = {}
    t = fighter_tint(ult)
    if t is not None and any(abs(v - 1.0) > 1e-6 for v in t):
        out.update({n: t for n in TINTED})
    for k, c in script_colours(scripts_dir).items():
        out[k] = tuple(a * b for a, b in zip(out.get(k, (1.0, 1.0, 1.0)), c))
    return out


def tint_args(ult, scripts_dir, overrides=None):
    """vfxb_to_ptcl.py --tint-for values (EFFECT=R:G:B, linear); port.json effects.tint_for overrides by name"""
    t = {k: '%g:%g:%g' % v for k, v in tints(ult, scripts_dir).items()}
    t.update(overrides or {})
    return [x for k, v in sorted(t.items()) for x in ('--tint-for', '%s=%s' % (k, v))]


if __name__ == '__main__':
    print('fighter tint:', fighter_tint(sys.argv[1]))
    for k, v in sorted(tints(*sys.argv[1:3]).items()):
        print('  %-28s %s' % (k, v))
