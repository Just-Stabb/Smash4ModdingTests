#!/usr/bin/env python3
"""Where the Ultimate (and vanilla Smash 4) files for ports live, so a port needs only its name.

  python3 tools/port_sources.py                 show what's configured and what each port finds
  python3 tools/port_sources.py NAME            the files found for one fighter (brave, pzenigame, ...)

Reads port_sources.json at the repository root (not committed: the paths are this machine's; copy
reference/port_sources.example.json), or the file named by $PORT_SOURCES. Every key is optional; a
list is searched in order:

  vanilla        Smash 4's dump root (fighter/<name>/script, param/fighter/fighter_param.bin, ...)
  labels         ParamLabels.csv (github.com/ultimate-research/param-labels)
  ult_common     Ultimate's fighter/common (param/fighter_param.prc, param/effect.prc)
  ult_fighters   folders holding Ultimate fighter folders <name>/ (model/, motion/, param/vl.prc ...)
  dumps          smashline dumps: folders holding lua2cpp_<name>/ (WuBoytH/SSBU-Dumped-Scripts)
  ult_effects    folders holding <name>/ef_<name>.eff (Ultimate's effect/fighter)
  ult_sound      Ultimate's sound/ (bank/fighter, bank/fighter_voice, sequence/fighter)
  ult_ui         Ultimate's ui/ folder or ui zip (portraits)
  vbn            folders holding <name>/model/body/c00/model.vbn (vanilla Smash 4 skeletons)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


class Sources(dict):
    def roots(self, key):
        v = self.get(key)
        return [] if v is None else [v] if isinstance(v, str) else list(v)

    def find(self, key, rel):
        """the first ROOT/rel that exists among key's roots"""
        for r in self.roots(key):
            p = os.path.join(r, rel)
            if os.path.exists(p):
                return p
        return None

    def ult_dir(self, ult):
        return self.find('ult_fighters', ult)

    def ult_file(self, ult, rel):
        d = self.ult_dir(ult)
        p = d and os.path.join(d, rel)
        return p if p and os.path.exists(p) else None

    def dump(self, ult):
        return self.find('dumps', 'lua2cpp_' + ult)

    def eff(self, ult):
        return self.find('ult_effects', '%s/ef_%s.eff' % (ult, ult))

    def report(self, ult):
        items = [('model', self.ult_file(ult, 'model/body/c00')), ('motions', self.ult_file(ult, 'motion/body/c00')),
                 ('motion_list', self.ult_file(ult, 'motion/body/c00/motion_list.bin')),
                 ('vl.prc', self.ult_file(ult, 'param/vl.prc')), ('dump', self.dump(ult)), ('effects', self.eff(ult)),
                 ('fighter_param.prc', self.find('ult_common', 'param/fighter_param.prc')),
                 ('labels', self.get('labels')),
                 ('sound', self.find('ult_sound', 'bank/fighter/se_%s.nus3audio' % ult)),
                 ('ui', self.roots('ult_ui')[0] if self.roots('ult_ui') else None)]
        return items


def load(path=None):
    path = path or os.environ.get('PORT_SOURCES') or os.path.join(ROOT, 'port_sources.json')
    if not os.path.exists(path):
        return Sources()
    return Sources(json.load(open(path)))


def kind_of(name):
    """a vanilla fighter's kind number from its internal name (fighter_param's order)"""
    sys.path.insert(0, HERE)
    import fighter_param
    return fighter_param.kind_of(name)


def ult_name(name):
    """the Ultimate fighter a port comes from: its port.json's "ult", else the same name"""
    p = os.path.join(ROOT, 'fighters', name, 'port.json')
    if os.path.exists(p):
        return json.load(open(p)).get('ult', name)
    return name


def main():
    s = load()
    if not s:
        sys.exit('no port_sources.json (copy reference/port_sources.example.json)')
    names = sys.argv[1:] or sorted(
        r['name'] for r in json.load(open(os.path.join(HERE, 'extra_kinds.json')))['kinds'])
    for n in names:
        u = ult_name(n)
        print('%s (Ultimate %s):' % (n, u))
        for k, v in s.report(u):
            print('  %-18s %s' % (k, v or '-- not found'))


if __name__ == '__main__':
    main()
