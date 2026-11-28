"""The clone's names in every language the creator's data has.

The game reads ui/message/melee.msbt from the data folder of the running region / language: the main one (data/ui/
message/melee.msbt) and, in a dump laid out as the console's content folder, the region partitions beside it
(data(us_en)/, data(us_fr)/, data(eu_de)/ ... each with its own ui/message/melee.msbt). The clone's MmelChara* labels
(name, capitals, title line, ...) go into every one found: the creator's title / title line, or a per-language override
(rec["titles"] = {"us_fr": {"title": ..., "subtitle": ...}, ...}). Each region's copy is written to
INSTALL_TO_data(<region>)/ui/message/melee.msbt beside INSTALL_TO_data.
"""
import argparse
import glob
import os
import re

from . import _paths  # noqa: F401
import msbt  # noqa: E402


def region_dirs(data_dir):
    """{region key: its data folder} of the data(<region>) folders beside data_dir"""
    parent = os.path.dirname(os.path.abspath(data_dir))
    out = {}
    for d in sorted(glob.glob(os.path.join(parent, 'data(*)'))):
        m = re.match(r'^data\((.+)\)$', os.path.basename(d))
        if m and os.path.isdir(d):
            out[m.group(1)] = d
    return out


def languages(data_dir):
    """[(key, melee.msbt path)]: 'main' and each region that has a melee.msbt"""
    out = []
    p = os.path.join(data_dir, 'ui', 'message', 'melee.msbt')
    if os.path.exists(p):
        out.append(('main', p))
    for k, d in region_dirs(data_dir).items():
        q = os.path.join(d, 'ui', 'message', 'melee.msbt')
        if os.path.exists(q):
            out.append((k, q))
    return out


def out_root(out_data, key):
    return out_data if key == 'main' else os.path.join(os.path.dirname(out_data), 'INSTALL_TO_data(%s)' % key)


def names(rec, data_dir, out_data):
    """the clone's labels in each region's melee.msbt (the main one is add_fighter.edit_msbt's); returns log lines"""
    import add_fighter as A
    logs = []
    titles = rec.get('titles') or {}
    for key, src in languages(data_dir):
        if key == 'main':
            continue
        root = out_root(out_data, key)
        cur = os.path.join(root, 'ui', 'message', 'melee.msbt')
        path = cur if os.path.exists(cur) else src
        data = open(path, 'rb').read()
        if ('MmelCharaN_01_%s' % rec['ui_name']).encode('utf-16-be') in data or \
                ('MmelCharaN_01_%s' % rec['ui_name']).encode() in data:
            logs.append('%s melee.msbt already has %s' % (key, rec['ui_name']))
            continue
        o = titles.get(key) or {}
        r = {'id': rec['ui_id'], 'base_ui': rec['source_ui'], 'ui_name': rec['ui_name'],
             'title': o.get('title') or rec.get('title') or rec['ui_name'],
             'subtitle': o.get('subtitle') or rec.get('subtitle')}
        sub = []
        A.edit_msbt([r], argparse.Namespace(msbt=path, ui=None, out=root), sub)
        logs.append('%s: ui/message/melee.msbt: %d labels for %s (%r)' % (key, sub[0].count(' = '), rec['ui_name'],
                                                                        r['title']))
    return logs


def check_all(reg, data_dir, out_data):
    """{key: [clone UI names missing their MmelCharaN_01_ label]} over every language"""
    out = {}
    for key, src in languages(data_dir):
        cur = os.path.join(out_root(out_data, key), 'ui', 'message', 'melee.msbt')
        m = msbt.Msbt(open(cur if os.path.exists(cur) else src, 'rb').read())
        out[key] = [f['ui_name'] for f in reg['fighters'] if 'MmelCharaN_01_%s' % f['ui_name'] not in m.labels]
    return out
