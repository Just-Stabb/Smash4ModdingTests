#!/usr/bin/env python3
"""Regenerate tools/sm4shclonetool/vendor/: the tool's own copies of the research modules it runs on.

  python3 tools/sm4shclonetool/make_vendor.py

Each copy is the research module (tools/<name>.py) with its comments and docstrings removed (the tool's docs
describe what it uses), a header of its own, the defaults pointed at the tool's code space instead of the research
repository's files, and the parts the tool doesn't use taken out (DROP / EDITS below). The result is parsed,
compiled and written with ast.unparse, so it is plain Python 3.9+.
"""
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'vendor')

# the tool's code space (sm4shclonetool/exe.py PARTS from 0x04B78000); exe.configure() sets them again
LAYOUT = {'dummy': 0x04B7BFF8, 'stage': (0x04B7C000, 0x04B7D000), 'customs': (0x04B7D000, 0x04B7E000),
          'effects': (0x04B7E000, 0x04B80000), 'kinds': (0x04B80000, 0x04BA8000), 'weapons': (0x04BA8000, 0x04BB8000)}

HEADERS = {
    'rpx_patch': 'Wii U RPX sections: load, decompress, patch 32-bit words by memory address, move relocations '
                 '(reloc:LO-HI=DUMMY), grow the code section (grow:END), raise the text region (textregion:SIZE), and '
                 'check that no patched word is still rewritten by a relocation at load time.',
    'rpx_compact': 'Rewrite an RPX with its sections packed again (no dead space left by moved sections).',
    'ppcasm': 'A small PowerPC assembler (the instructions the patches use, labels, ha / lo).',
    'kind_expand': 'New fighter kinds 0x41 and up: the per-kind tables (names, special-block sizes, sound class, '
                   'character names), the six 65-case kind switches, the parameter manager\'s per-kind arrays (moved '
                   'to a larger allocation), the kind-count bounds, the save\'s per-character records, the sound '
                   'files\' name tables, and per new kind its descriptor, motion table and vl load / unload cases, '
                   'all copied from its base kind. Reads a kinds spec (JSON) and a vanilla RPX; every hooked word is '
                   'checked against the game\'s original.',
    'weapon_expand': 'New weapon (article) kinds for new fighter kinds: copies of the base fighter\'s articles owned '
                     'by the new fighter (their files load from its folder): the weapon tables, the 13 weapon-kind '
                     'switches, descriptors, the module rows, kind compares, and the new fighter\'s article list.',
    'base_effects_cave': 'A new fighter kind also registers / releases its base kind\'s effect banks (its articles\' '
                         'effects use the base\'s ids): wrappers at the effect-folder and bank call sites.',
    'base_customs_cave': 'Custom moves: a new character id owns its base character\'s custom moves (the owned-move '
                         'index functions map the new id to the base\'s).',
    'stage_slot_cave': 'New stage slots: stage kinds past the game\'s 128 (0x80 + 2i normal, 0x81 + 2i Omega) and '
                       'stage-select cosmetic ids from 0x38: the stage-kind table, the cosmetic name table, the counts '
                       'and the page-2 checks. Some addresses were first found by Manifold (Fitz Null, zlib licence, '
                       'https://gitlab.com/fitz.lol/manifold).',
    's4param': 'Smash 4 parameter files (.bin, PARAM groups): parse and build byte for byte.',
    'msbt': 'MSBT text files (labels, UTF-16 texts): read and write.',
    'add_fighter': 'The data files of a new fighter kind copied from a base: param / UI database rows, names '
                   '(melee.msbt), portraits with new texture ids, the renamed fighter folder (ACMD effect ids moved to '
                   'the new kind). Every edited file is checked: without the new rows it rebuilds byte for byte.',
    'add_stage': 'The data files of a new stage slot copied from a stage: stage-select / song database entries, '
                 'names, icons (new texture ids) and the renamed stage folders.',
    'add_fighter_customs': 'Custom-move names (menu.msbt MmenSpN__ / MmenSpI__ labels) and icons (spi_10) of a new '
                           'character, copied from its base.',
    'acmd': 'ACMD script files (the game\'s animcmd .bin): read, edit and write; command table in acmd_info.json '
            '(from Sammi Husky\'s SALT, MIT).',
    'nut': 'Smash 4 Wii U textures (.nut, NTWU / NTP3): read a texture to RGBA and write one back. Header layout and '
           'the GX2 (de)swizzle follow Smash Forge\'s NUT.cs / GTX.cs (MIT; GTX.cs ports AboodXD\'s GTX Extractor).',
    'result_param': 'param/ui/result_param.bin: the results scene\'s per-fighter framing (the loser panel camera eye / '
                    'target and the win poses\' frames), keyed by the fighter\'s model (folder) name: read and add entries.',
    'chara_layout': 'Lumen (.lm) files: read the character select\'s face-layout sprite (frames num_NNN, places '
                    'face_NNN) and simulate its display list.',
}

# functions / classes taken out (with the statements that call them); UPPERCASE names: module constants taken out
DROP = {
    'weapon_expand': {'kirby_copy', 'main', 'KIRBY_COPY_TABLE', 'KIRBY_COPY_RES', 'KIRBY_RESERVE'},
    'kind_expand': {'rescan_ram', 'main'},
    'base_effects_cave': {'main'}, 'base_customs_cave': {'main'}, 'stage_slot_cave': {'main'},
    'acmd': {'_new_commands', 'new_var', 'main'},
    'chara_layout': {'user4', 'user5', 'relayout', 'sheet', 'main', 'keyframes_match', 'STYLES', 'ROWS_Y',
                     'ODD_X0', 'EVEN_X0', 'DX'},
    'add_fighter': {'main', 'load_records', 'KINDS'}, 'add_stage': {'main'},
    'nut': {'main'},
    'result_param': {'main'},
}

# source edits before parsing: (module, old, new); old must be found
EDITS = [
    ('kind_expand', "SPEC = os.path.join(HERE, 'extra_kinds.json')", 'SPEC = None'),
    ('kind_expand', "RPX = os.path.join(HERE, '..', 'build', 'cross_f.rpx')", 'RPX = None'),
    ('kind_expand', 'CAVE = 0x04BA0000', 'CAVE = 0x%08X' % LAYOUT['kinds'][0]),
    ('kind_expand', 'LIMIT = 0x04BB0000', 'LIMIT = 0x%08X' % LAYOUT['kinds'][1]),
    ('kind_expand', 'RELOC_DUMMY = 0x037EE73C', 'RELOC_DUMMY = 0x%08X' % LAYOUT['dummy']),
    # the random-select pool is 96 bits (ids 0-95): scan at most that many entries (later ids are left out of random;
    # sm4shclonetool/random_select.py patches the pool's other two bounds and the per-clone choice)
    ('kind_expand', """    n_sel = RANDOM_SELECT_COUNT + len(uis)
    assert n_sel <= 96, 'the random-select set holds 96 database entries'""",
     """    n_sel = min(96, RANDOM_SELECT_COUNT + len(uis))"""),
    ('weapon_expand', 'CAVE = 0x04BB0000', 'CAVE = 0x%08X' % LAYOUT['weapons'][0]),
    ('weapon_expand', 'LIMIT = 0x04BB8000', 'LIMIT = 0x%08X' % LAYOUT['weapons'][1]),
    ('weapon_expand', """                if 'kirby_copy' in spec:
                    r.setdefault('kirby_copy', {})[nk] = int(spec['kirby_copy'])
""", ''),
    ('base_effects_cave', 'CAVE = 0x04B88000', 'CAVE = 0x%08X' % LAYOUT['effects'][0]),
    ('base_effects_cave', 'LIMIT = 0x04B89000', 'LIMIT = 0x%08X' % LAYOUT['effects'][1]),
    ('base_customs_cave', 'CAVE = 0x04B8A000', 'CAVE = 0x%08X' % LAYOUT['customs'][0]),
    ('base_customs_cave', 'LIMIT = 0x04B8B000', 'LIMIT = 0x%08X' % LAYOUT['customs'][1]),
    ('base_customs_cave', "SPEC = os.path.join(HERE, 'extra_kinds.json')", 'SPEC = None'),
    ('base_customs_cave', "RPX = os.path.join(HERE, '..', 'build', 'cross_f.rpx')", 'RPX = None'),
    ('stage_slot_cave', "RPX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'cave_fix_s4', "
                        "'cross_f.rpx')", 'RPX = None'),
    ('stage_slot_cave', 'CAVE = 0x04B7C000', 'CAVE = 0x%08X' % LAYOUT['stage'][0]),
    ('stage_slot_cave', 'LIMIT = 0x04B7D000', 'LIMIT = 0x%08X' % LAYOUT['stage'][1]),
    ('stage_slot_cave', 'RELOC_DUMMY = 0x037EE73C', 'RELOC_DUMMY = 0x%08X' % LAYOUT['dummy']),
    ('add_fighter', 'from fighter_param import KINDS  # noqa: E402', 'KINDS = None'),
    ('acmd', '_new_commands()\n', ''),
    ('nut', "mode='edge'", "mode='symmetric'"),
    ('add_fighter', "its own weapons (tools/weapon_expand.py; files", "its own weapons (new weapon kinds; files"),
    ('add_fighter_customs', "(the user's: replace/customize)", "(yours: replace/customize)"),
    ('add_fighter_customs', "    ap.add_argument('--kinds', default=os.path.join(HERE, 'extra_kinds.json'))",
     "    ap.add_argument('--kinds', required=True)"),
]
# names in the copies that must be gone (the check after writing; tests/package_clean_test.py checks the zip)
FORBIDDEN = re.compile(r'supamario|squirtle|zenigame|byleth|sephiroth|\bedge\b|\bbrave\b|\bmaster\b|gaogaen|incineroar|'
                       r'pickel|\bsteve\b|kamehameha|extra_kinds\.json|fighters/|docs/|exe_v4|gekkouga_clone|cave_fix|'
                       r'poketrainer|037EE73C|KIRBY_COPY_TABLE|KIRBY_RESERVE|user4|user5|tools/', re.I)


class Strip(ast.NodeTransformer):
    def __init__(self, drop):
        self.drop = drop

    def _body(self, body):
        out = []
        for i, st in enumerate(body):
            if i == 0 and isinstance(st, ast.Expr) and isinstance(getattr(st, 'value', None), ast.Constant) \
                    and isinstance(st.value.value, str):
                continue                                   # docstring
            if isinstance(st, (ast.FunctionDef, ast.ClassDef)) and st.name in self.drop:
                continue
            if isinstance(st, ast.Assign) and any(n.id in self.drop and n.id.isupper() for t in st.targets
                                                  for n in ast.walk(t) if isinstance(n, ast.Name)):
                continue
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and \
                    isinstance(st.value.func, ast.Name) and st.value.func.id in self.drop:
                continue
            if isinstance(st, ast.If) and 'main' in self.drop and ast.unparse(st.test) == "__name__ == '__main__'":
                continue
            out.append(st)
        return out or [ast.Pass()]

    def generic_visit(self, node):
        for field in ('body', 'orelse', 'finalbody'):
            if isinstance(getattr(node, field, None), list) and getattr(node, field) and \
                    isinstance(getattr(node, field)[0], ast.stmt):
                setattr(node, field, self._body(getattr(node, field)))
        for h in getattr(node, 'handlers', []) or []:
            h.body = self._body(h.body)
        return super().generic_visit(node)


def make(name):
    src = open(os.path.join(TOOLS, name + '.py')).read()
    for mod, old, new in EDITS:
        if mod == name:
            assert old in src, '%s: edit not found: %r' % (name, old[:60])
            src = src.replace(old, new)
    tree = ast.parse(src)
    tree = Strip(DROP.get(name, set())).visit(tree)
    head = HEADERS[name]
    words, lines, cur = head.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > 112:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    lines.append(cur)
    doc = '"""%s\n\nAdapted for Sm4shCloneTool from the Smash 4 research tools (comments and unused parts taken out; ' \
          'the tool\nsets the code addresses itself, see its README "The executable")."""\n' % '\n'.join(lines)
    code = doc + ast.unparse(ast.fix_missing_locations(tree)) + '\n'
    compile(code, name + '.py', 'exec')
    open(os.path.join(OUT, name + '.py'), 'w').write(code)
    bad = sorted({m.group(0) for m in FORBIDDEN.finditer(code)})
    return len(code.splitlines()), bad


def acmd_info():
    info = json.load(open(os.path.join(TOOLS, 'acmd_info.json')))
    sys.path.insert(0, TOOLS)
    import zlib
    import acmd_ext_cave as ext                 # the research's own added commands: taken out
    names = {n for n, *_r in ext.NEW_CMDS} | {'New_Var'}
    ids = {'%08X' % (zlib.crc32(n.encode()) & 0xFFFFFFFF) for n in names}
    cmds = {k: v for k, v in info['commands'].items() if k.upper().zfill(8) not in ids and v.get('name') not in names}
    out = {'_source': 'The game\'s ACMD commands, from SALT (Sammi Husky, MIT license) Scripting/AnimCMD/CMD_INFO.cs',
           'commands': cmds}
    json.dump(out, open(os.path.join(OUT, 'acmd_info.json'), 'w'), indent=0)
    return len(info['commands']), len(cmds)


def ram_json():
    d = json.load(open(os.path.join(TOOLS, 'kind_expand_ram.json')))
    d['about'] = ('the parameter manager\'s per-kind accesses with a variable kind (address, original word, array, '
                  'instruction): the kind expansion moves their immediates to the relocated arrays')
    with open(os.path.join(OUT, 'kind_expand_ram.json'), 'w') as f:
        f.write('{"about": %s,\n "kept": %s,\n "sites": [\n' % (json.dumps(d['about']), json.dumps(d['kept'])))
        f.write(',\n'.join('  ' + json.dumps(x) for x in d['sites']))
        f.write('\n ]}\n')
    return len(d['sites'])


def main():
    os.makedirs(OUT, exist_ok=True)
    bad_all = 0
    for name in HEADERS:
        n, bad = make(name)
        print('%-22s %5d lines%s' % (name, n, ('  STILL: ' + ', '.join(bad)) if bad else ''))
        bad_all += len(bad)
    old, new = acmd_info()
    print('acmd_info.json: %d -> %d commands (the game\'s)' % (old, new))
    print('kind_expand_ram.json: %d sites' % ram_json())
    open(os.path.join(OUT, 'VENDORED.txt'), 'w').write(
        'Sm4shCloneTool\'s own copies of the Smash 4 research tools it runs on (the executable research: the kind,\n'
        'weapon, effect-bank, custom-move and stage-slot patches; the data-file, text, texture, ACMD and layout\n'
        'readers). Adapted: comments and unused parts taken out, the defaults set to the tool\'s code space\n'
        '(0x04B78000-0x04BB8000). acmd_info.json: the game\'s ACMD commands (SALT, Sammi Husky, MIT).\n'
        'kind_expand_ram.json: the game\'s per-kind array sites (static analysis of the game\'s cross_f.rpx).\n'
        'dspadpcm.py (1.3): the DSP-ADPCM encoder, a Python port of jackoalan\'s gc-dspadpcm-encode grok.c (MIT); written for\n'
        'the tool (not generated by make_vendor.py, which leaves it as it is).\n'
        'Credits and licences: ../THIRD_PARTY.txt.\n')
    sys.exit(1 if bad_all else 0)


if __name__ == '__main__':
    main()
