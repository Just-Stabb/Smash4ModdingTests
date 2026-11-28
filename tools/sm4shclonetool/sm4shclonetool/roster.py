"""The roster: the fighters and stages a creator's files have (vanilla ones from the game's databases and
name tables, clones from the tool's registry), and the settings / registry kept in the project file."""
import json
import os

from . import _paths  # noqa: F401
import s4param  # noqa: E402

PROJECT = 'sm4shclonetool_project.json'
# fighter kind -> lowercase folder name / Capitalised file name (the executable's tables 0x102FF484 / 0x102FF588)
KINDS = ['miifighter', 'miiswordsman', 'miigunner', 'mario', 'donkey', 'link', 'samus', 'yoshi', 'kirby', 'fox',
         'pikachu', 'luigi', 'captain', 'ness', 'peach', 'koopa', 'zelda', 'sheik', 'marth', 'gamewatch', 'ganon',
         'falco', 'wario', 'metaknight', 'pit', 'szerosuit', 'pikmin', 'diddy', 'dedede', 'ike', 'lucario', 'robot',
         'toonlink', 'lizardon', 'sonic', 'purin', 'mariod', 'lucina', 'pitb', 'rosetta', 'wiifit', 'littlemac',
         'murabito', 'palutena', 'reflet', 'duckhunt', 'koopajr', 'shulk', 'gekkouga', 'pacman', 'rockman',
         'mewtwo', 'ryu', 'lucas', 'roy', 'cloud', 'bayonetta', 'kamui', 'koopag', 'warioman', 'littlemacg',
         'lucariom', 'miienemyf', 'miienemys', 'miienemyg']
# character id -> UI name (portrait files, MmelChara labels; the executable's table 0x1033BE68)
UI_NAMES = ['Omakase', 'Miifighter', 'Miiswordsman', 'Miigunner', 'Mario', 'Donkey', 'Link', 'Samus', 'Yoshi',
            'Kirby', 'Fox', 'Pikachu', 'Luigi', 'Captain', 'Ness', 'Peach', 'Koopa', 'Zelda', 'Sheik', 'Marth',
            'Gamewatch', 'Ganon', 'Falco', 'Wario', 'Metaknight', 'Pit', 'Szerosuit', 'Pikmin', 'Diddy',
            'Dedede', 'Ike', 'Lucario', 'Robot', 'Toonlink', 'Lizardon', 'Sonic', 'Drmario', 'Rosetta',
            'Wiifit', 'Littlemac', 'Murabito', 'Palutena', 'Reflet', 'Duckhunt', 'KoopaJr', 'Shulk', 'Purin',
            'Lucina', 'Pitb', 'Gekkouga', 'Pacman', 'Rockman', 'Mewtwo', 'Ryu', 'Lucas', 'Roy', 'Cloud',
            'Bayonetta', 'Kamui']
# stage kinds 0x00-0x2E (stage/melee/<name>), the executable's stage-kind table 0x1011D95C
MELEE_KINDS = ['BattleField_f', 'End_f', 'Galaxy', 'MarioU', 'MarioKart', 'Kalos', 'Skyward', 'DKReturns',
               'Metroid', 'YoshiU', 'Cave', 'Village2', 'Assault', 'Colloseum_f', 'PikminU', 'Angeland',
               'Gamer', 'DuckHunt', 'Wrecking', 'XenoBlade', 'PunchOut', 'PunchOut2', 'Wufu', 'Miiverse',
               'WiiFit', 'Pilotwings', 'Windyhill', 'Pacland', 'Wily', 'Gw3', 'XDolpic', 'XKart', 'XStadium',
               'XOldin', '64Jungle', 'XNorfair', 'DxYorster', 'XHalberd', 'XVillage', 'XStarfox', 'XEmblem',
               'XPalutena', 'XFzero', 'DxOnett', 'XDonkey', 'DxShrine', 'XMansion']
# Kirby-copy-style "trait" of nothing: Kirby can't copy a new kind (vanilla copy_grant refuses kinds >= 0x3A)
NO_BASE = {0, 1, 2}                  # the Miis: their files and params are Mii-specific (not offered as bases)


def group(items):
    return next(it for it in items if isinstance(it, list) and it[0] == 'group')


def first(dirs, rel):
    for d in dirs:
        if d and os.path.exists(os.path.join(d, rel)):
            return os.path.join(d, rel)
    return None


def load_db(dirs, rel):
    p = first(dirs, rel)
    if not p:
        return None, None
    data = open(p, 'rb').read()
    return group(s4param.parse(data)), p


# ---------------------------------------------------------------- project
def empty_registry():
    return {'fighters': [], 'stages': []}


def load_project(out_dir):
    p = os.path.join(out_dir, PROJECT)
    if os.path.exists(p):
        return json.load(open(p))
    return {'tool': 'Sm4shCloneTool', 'registry': empty_registry(), 'settings': {}, 'builds': []}


def save_project(out_dir, proj):
    os.makedirs(out_dir, exist_ok=True)
    json.dump(proj, open(os.path.join(out_dir, PROJECT), 'w'), indent=1, sort_keys=True)


# ---------------------------------------------------------------- fighters
def fighters(param_dirs, reg):
    """[{id, kind, name, cap, ui_name, series, costumes, sort, dlc, clone, record}] of every character the
    database shows (vanilla ids 1-58 and clones), in id order"""
    g, _p = load_db(param_dirs, 'ui/ui_character_db.bin')
    if g is None:
        raise FileNotFoundError('param/ui/ui_character_db.bin not found in %s' % ', '.join(d for d in param_dirs if d))
    clones = {f['ui_id']: f for f in reg['fighters']}
    out = []
    for e in g[2]:
        cid = e[0][1]
        if cid >= 200 or e[5][1] != 1:
            continue
        kind = e[6][1]
        c = clones.get(cid)
        if c:
            name, cap, ui = c['name'], c['cap'], c['ui_name']
        elif kind < len(KINDS) and cid < len(UI_NAMES):
            name, cap, ui = KINDS[kind], None, UI_NAMES[cid]
        else:
            name, cap, ui = 'kind%02x' % kind, None, 'Id%d' % cid
        out.append({'id': cid, 'kind': kind, 'name': name, 'ui_name': ui, 'series': e[4][1], 'costumes': e[7][1],
                    'sort': [e[13 + j][1] for j in range(3)], 'dlc': e[10][1], 'mii': e[9][1],
                    'clone': bool(c), 'record': c, 'shown': e[2][1]})
    return out


def base_choices(param_dirs, reg):
    return [f for f in fighters(param_dirs, reg) if f['kind'] not in NO_BASE]


def css_entries(param_dirs, reg):
    """the character select's entries in its order: the non-DLC entries (and random) by their first sort key,
    then the DLC ones by theirs (the list builder 0x028BF6AC, sort 0x028BE798 by +0x20, 0x030A0874); equal keys by
    id (assumed: the game's sort isn't stable)"""
    fs = [f for f in fighters(param_dirs, reg) if f['shown']]
    g, _p = load_db(param_dirs, 'ui/ui_character_db.bin')
    rnd = next((e for e in g[2] if e[0][1] == 0), None)
    if rnd is not None:
        fs.append({'id': 0, 'kind': -1, 'name': 'random', 'ui_name': 'Omakase', 'sort': [rnd[13][1]] * 3,
                   'dlc': 0, 'clone': False, 'record': None})
    have = {f['id'] for f in fs}
    top = max(e[13][1] for e in g[2] if e[0][1] < 200) + 1
    for c in reg['fighters']:              # planned clones (not in the database yet)
        if c['ui_id'] not in have:
            s = c.get('sort') or [top] * 3
            fs.append({'id': c['ui_id'], 'kind': c['kind'], 'name': c['name'], 'ui_name': c['ui_name'],
                       'sort': list(s), 'dlc': 0, 'clone': True, 'record': c, 'planned': True})
            for f in fs:
                if f['id'] in c.get('renumber', ()):
                    f['sort'] = [f['sort'][0] + 1] + f['sort'][1:]
            top = max(top, s[0] + 1)
    main = sorted([f for f in fs if not f['dlc']], key=lambda f: (f['sort'][0], f['id']))
    dlc = sorted([f for f in fs if f['dlc']], key=lambda f: (f['sort'][0], f['id']))
    return main + dlc


# ---------------------------------------------------------------- stages
STAGE_NAMES = None                  # the executable's stage-kind names (set by the session), else MELEE_KINDS


def stage_kind_names(exe_path):
    """the folder names of the game's 128 stage kinds, from the executable's table 0x1011D95C ({name, variant})"""
    from .rpx import Rpx
    x = Rpx(exe_path)
    return [x.cstr(x.r32(0x1011D95C + 8 * k)) for k in range(0x80)]


def stages(param_dirs, reg):
    """[{id (cosmetic), kind, name, page, order, clone}] of the stage select's stages"""
    g, _p = load_db(param_dirs, 'ui/ui_stage_db.bin')
    if g is None:
        raise FileNotFoundError('param/ui/ui_stage_db.bin not found')
    clones = {s['cosmetic']: s for s in reg['stages']}
    out = []
    for e in g[2]:
        cos = e[0][1]
        if cos >= 0xC8 or not e[1][1]:
            continue
        kind = e[6][1]
        c = clones.get(cos)
        if c:
            name = c['name']
        elif STAGE_NAMES and kind < len(STAGE_NAMES):
            name = STAGE_NAMES[kind]
        elif kind < len(MELEE_KINDS):
            name = MELEE_KINDS[kind]
        else:
            name = 'stage%02x' % kind
        out.append({'id': cos, 'kind': kind, 'name': name, 'page': 2 if e[3][1] else 1, 'order': e[10][1],
                    'series': e[2][1], 'clone': bool(c), 'record': c})
    return out


def sss_pages(param_dirs, reg):
    ss = stages(param_dirs, reg)
    have = {s['id'] for s in ss}
    top = max([s['order'] for s in ss] or [0]) + 1
    for c in reg['stages']:                # planned clones
        if c['cosmetic'] not in have:
            ss.append({'id': c['cosmetic'], 'kind': c['kind'], 'name': c['name'], 'page': c.get('page', 1),
                       'order': c.get('order') or top, 'clone': True, 'record': c, 'planned': True})
            top += 1
    return {p: sorted([s for s in ss if s['page'] == p], key=lambda s: (s['order'], s['id'])) for p in (1, 2)}
