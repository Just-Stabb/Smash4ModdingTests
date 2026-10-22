#!/usr/bin/env python3
"""Customize-menu data a new character is missing (add_fighter.py leaves them out; run it after add_fighter.py, with --used-ui its output's ui):

  python3 tools/add_fighter_customs.py --ui VANILLA_UI --menu USER_menu.msbt --used-ui BUILT_UI_DIR... --out OUT [--kinds K]

- ui/message/menu.msbt: MmenSpN__<New>_<Nt|Sd|Up|Dw>_<1-3> (special names) and MmenSpI__... (their
  descriptions) = the base's, built on the given menu.msbt (the user's own, so nothing else changes);
  the Customize menu builds these labels from the UI name (0x02342CF4 'MmenSpN__%s_Nt_%d').
- ui/replace/customize/spi_10/spi_10_<New>_<slot>_<n>.nut: the special-move icons (0x029170EC,
  'spi_10_%s_%s_%d', ui/replace[/append]/customize/spi_10), the base's with new texture ids.
New texture ids continue the character's block (0x28010000 + 0x100 * (id - 59)) past every id in use.
"""
import argparse
import json
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import msbt  # noqa: E402
from add_stage import texture_ids, used_texture_ids  # noqa: E402
import struct  # noqa: E402

NEW_TEXTURE_IDS = 0x28010000
UI_NAMES = {'mario': 'Mario'}       # base fighter name -> its UI name, where the record doesn't say


def records(path):
    out = []
    for r in json.load(open(path))['kinds']:
        ui = r.get('ui') or {}
        if ui.get('id') is None:
            continue
        out.append({'id': int(str(ui['id']), 0), 'name': ui.get('name') or r.get('cap'),
                    'base_ui': ui.get('base_name') or UI_NAMES.get(r['base'], r['base'].capitalize())})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ui', required=True, help="the ui folder the game shows (the user's: replace/customize)")
    ap.add_argument('--menu', required=True, help='menu.msbt to add the labels to')
    ap.add_argument('--used-ui', action='append', default=[], help='ui folders whose texture ids are taken')
    ap.add_argument('--kinds', default=os.path.join(HERE, 'extra_kinds.json'))
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    recs = records(a.kinds)
    log = []

    data = open(a.menu, 'rb').read()
    m = msbt.Msbt(data)
    assert m.build() == data, 'menu.msbt: round trip differs'
    old = {lab: m.text(lab) for lab in m.labels}
    added = []
    for r in recs:
        pat = re.compile(r'^MmenSp([NI])__%s_(Nt|Sd|Up|Dw)_(\d)$' % re.escape(r['base_ui']))
        for lab in sorted(old):
            mm = pat.match(lab)
            if mm:
                new = 'MmenSp%s__%s_%s_%s' % (mm.group(1), r['name'], mm.group(2), mm.group(3))
                assert new not in old, new
                m.set(new, old[lab])
                added.append(new)
        assert any(x.startswith('MmenSpN__%s_' % r['name']) for x in added), 'no MmenSpN__%s_ labels' % r['base_ui']
    dst = os.path.join(a.out, 'ui', 'message', 'menu.msbt')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(m.build())
    chk = msbt.Msbt(open(dst, 'rb').read())
    assert all(chk.text(l) == t for l, t in old.items()), 'an old label changed'
    for idx in sorted((chk.labels.pop(l) for l in added), reverse=True):
        assert idx == len(chk.texts) - 1
        chk.texts.pop()
    assert chk.build() == data, 'without the new labels it differs from the input'
    log.append('ui/message/menu.msbt (from %s): +%d labels %s' % (a.menu, len(added), ', '.join(added)))

    used = set()
    for d in [a.ui] + a.used_ui:
        used |= used_texture_ids(d)
    for r in recs:
        tex = NEW_TEXTURE_IDS + 0x100 * (r['id'] - 59)
        for sub, rx in (('replace/customize/spi_10', r'spi_10_%s_(Nt|Sd|Up|Dw)_\d\.nut$'),
                        ('replace/append/customize/spi_10', r'spi_10_%s_(Nt|Sd|Up|Dw)_\d\.nut$')):
            src = os.path.join(a.ui, sub)
            if not os.path.isdir(src):
                continue
            for f in sorted(os.listdir(src)):
                if not re.match(rx % re.escape(r['base_ui']), f):
                    continue
                blob = open(os.path.join(src, f), 'rb').read()
                if blob[:2] == b'\x78\x9c':
                    blob = zlib.decompress(blob)
                blob = bytearray(blob)
                ids = []
                for off, _ in texture_ids(blob):
                    while tex in used:
                        tex += 1
                    used.add(tex)
                    struct.pack_into('>I', blob, off, tex)
                    ids.append(tex)
                nf = f.replace('_%s_' % r['base_ui'], '_%s_' % r['name'], 1)
                dst = os.path.join(a.out, 'ui', sub, nf)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(bytes(blob))
                log.append('ui/%s/%s (texture %s)' % (sub, nf, ', '.join('0x%08X' % t for t in ids)))
    print('\n'.join(log))


if __name__ == '__main__':
    main()
