#!/usr/bin/env python3
"""Sm4shCloneTool, command line.

  python cli.py info    --exe cross_f.rpx                       what the executable is (vanilla / patched / other)
  python cli.py roster  --data DATA [--exe EXE] [--out OUT]     fighters and stages, with the clones
  python cli.py check   --data DATA --out OUT [--exe EXE] [--ui UI] CLONES...   validate, list the files and patches
  python cli.py build   --data DATA --out OUT [--exe EXE] [--ui UI] CLONES...   write the package
  python cli.py css     --data DATA --out OUT [--ui UI] [--exe EXE] [--png FILE] [CLONES...]   CSS preview
  python cli.py sss     ...                                                                    SSS preview

CLONES:
  --fighter SOURCE:NAME[:key=value,...]   e.g. --fighter fox:foxclone:ui_name=Wolfo,title=Wolfo,costumes=8
       keys: cap, ui_name, title, subtitle, series, costumes, after (place after this character on the CSS),
             sort_key (first sort key), weapons (article names joined by +), customs (1), fanfare (0 / 1),
             kind, ui_id (overrides; must be the next free ones)
  --portrait NAME:SET:NN=PNG              e.g. --portrait foxclone:chr_00:01=red.png  (NN empty for one-file sets)
  --stage SOURCE:NAME[:key=value,...]     e.g. --stage BattleField_f:CloneField:title=Clone Field,page=1
       keys: title, series, page (1 / 2), cosmetic
  --stage-icon NAME:SET=PNG
  --force                                 patch an executable that is not vanilla (another mod's code space) anyway
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sm4shclonetool import VERSION  # noqa: E402
from sm4shclonetool import exe as X  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402

INTS = {'costumes', 'series', 'sort_key', 'kind', 'ui_id', 'page', 'cosmetic', 'customs', 'fanfare'}


def kv(text):
    out = {}
    for part in filter(None, text.split(',')):
        k, _, v = part.partition('=')
        out[k] = int(v, 0) if k in INTS else v
    return out


def parse_clones(a, s):
    fighters, stages, portraits, icons = [], [], {}, {}
    for f in a.fighter or []:
        src, name, *rest = f.split(':', 2)
        opt = kv(rest[0]) if rest else {}
        if 'weapons' in opt:
            opt['weapons'] = [w for w in opt['weapons'].split('+') if w]
        if 'customs' in opt:
            opt['customs'] = bool(opt['customs'])
        if 'fanfare' in opt:
            opt['fanfare'] = bool(opt['fanfare'])
        fighters.append(opt.pop('_spec', None) or s.fighter_spec(src, name, **opt))
        if fighters[-1]['kind'] is None:
            pass
    for p in a.portrait or []:
        left, png = p.split('=', 1)
        name, st, nn = left.split(':')
        portraits.setdefault(name, {})[(st, nn)] = png
    for st in a.stage or []:
        src, name, *rest = st.split(':', 2)
        opt = kv(rest[0]) if rest else {}
        stages.append(s.stage_spec(src, name, **opt))
    for p in a.stage_icon or []:
        left, png = p.split('=', 1)
        name, st = left.split(':')
        icons.setdefault(name, {})[st] = png
    # several fighters in one call: the later ones get the next slots
    for i, f in enumerate(fighters):
        f['kind'] = f['kind'] + i if i and f['kind'] == fighters[0]['kind'] else f['kind']
        f['ui_id'] = f['ui_id'] + i if i and f['ui_id'] == fighters[0]['ui_id'] else f['ui_id']
    for i, st in enumerate(stages):
        st['cosmetic'] = st['cosmetic'] + i if i and st['cosmetic'] == stages[0]['cosmetic'] else st['cosmetic']
    return fighters, stages, portraits, icons


def main():
    ap = argparse.ArgumentParser(description='Sm4shCloneTool %s' % VERSION, epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'roster', 'check', 'build', 'css', 'sss'])
    ap.add_argument('--data')
    ap.add_argument('--ui')
    ap.add_argument('--exe')
    ap.add_argument('--out')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--fighter', action='append')
    ap.add_argument('--portrait', action='append')
    ap.add_argument('--stage', action='append')
    ap.add_argument('--stage-icon', action='append')
    ap.add_argument('--png')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if a.command == 'info':
        info = X.inspect(a.exe)
        if a.json:
            print(json.dumps(info, indent=1))
            return
        print('%s: %s (SHA-1 %s%s)' % (a.exe, info['state'], info['sha1'],
                                       ', the research base' if info['research_sha1'] else ''))
        for p in info.get('problems', []):
            print('  ' + p)
        for f in info['registry']['fighters']:
            print('  fighter clone %s kind 0x%X id %d from %s' % (f['name'], f['kind'], f['ui_id'], f['source']))
        for st in info['registry']['stages']:
            print('  stage clone %s cosmetic 0x%X from %s' % (st['name'], st['cosmetic'], st['source']))
        return
    s = Session(a.data, a.out or os.path.join(os.getcwd(), 'sm4shclonetool_out'), a.exe, a.ui, a.force)
    if a.command == 'roster':
        for f in R.fighters(s.param_dirs(), s.reg):
            print('%3d %-14s kind 0x%02X %-12s sort %s%s' % (f['id'], f['ui_name'], f['kind'], f['name'],
                                                           f['sort'], ' (clone)' if f['clone'] else ''))
        for st in R.stages(s.param_dirs(), s.reg):
            print('stage 0x%02X %-16s kind 0x%02X page %d order %d%s' % (st['id'], st['name'], st['kind'], st['page'],
                                                                     st['order'], ' (clone)' if st['clone'] else ''))
        return
    fighters, stages, portraits, icons = parse_clones(a, s)
    if a.command == 'check':
        reg, recs, errors, notes, files, items = s.plan(fighters, stages)
        for n in notes:
            print('note: ' + n)
        for e in errors:
            print('ERROR: ' + e)
        print('files:')
        for f in files:
            print('  ' + f)
        print('executable:')
        for i in items:
            print('  ' + i)
        sys.exit(1 if errors else 0)
    if a.command in ('css', 'sss'):
        reg = s.plan(fighters, stages)[0]
        new = [f['ui_id'] for f in reg['fighters']] if a.command == 'css' else [x['cosmetic'] for x in reg['stages']]
        _img, info = (s.css if a.command == 'css' else s.sss)(reg, new, a.png or a.command + '.png')
        print(json.dumps({k: v for k, v in info.items() if k != 'slot'}, default=str)[:2000])
        return
    summary = s.build(fighters, stages, portraits, icons)
    print('built: %s -> %s' % (', '.join(summary['clones']), s.out))


if __name__ == '__main__':
    main()
