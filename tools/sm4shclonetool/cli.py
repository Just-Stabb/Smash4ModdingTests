#!/usr/bin/env python3
"""Sm4shCloneTool, command line.

  python cli.py info    --exe cross_f.rpx                       what the executable is (vanilla / patched / other)
  python cli.py roster  --data DATA [--exe EXE] [--out OUT]     fighters and stages, with the clones
  python cli.py check   --data DATA --out OUT [--exe EXE] [--ui UI] CLONES...   validate, list the files and patches
  python cli.py build   --data DATA --out OUT [--exe EXE] [--ui UI] CLONES...   write the package
  python cli.py css     --data DATA --out OUT [--ui UI] [--exe EXE] [--png FILE] [CLONES...]   CSS preview
  python cli.py sss     ...                                                                    SSS preview
  python cli.py voices  --out OUT --data DATA --name CLONE [--replace TONE=WAV ...] [--import-folder DIR]
                        list a built clone's voice / sound lines by category; replace lines with WAVs (its own banks)
  python cli.py plate   --text TEXT [--set chrn_40] [--font FILE] [--lines 1|2] --png OUT.png   a name plate preview

CLONES:
  --fighter SOURCE:NAME[:key=value,...]   e.g. --fighter fox:foxclone:ui_name=Wolfo,title=Wolfo,costumes=8
       keys: cap, ui_name, title, subtitle, series, costumes, after (place after this character on the CSS),
             sort_key (first sort key), weapons (article names joined by +), customs (1), fanfare (0 / 1),
             random (0: never picked by the character select's random),
             own_sound / own_effects (1 by default: its own sound banks / effect bank; 0: the base's),
             weapons: all (default) / none / names joined by + (its own articles),
             kind, ui_id (overrides; must be the next free ones),
             call: own (default: its own copy of the base's announcer call) / share / a .wav file,
             music: own (default: its own copy of the base's victory fanfare) / share / a .wav file,
             kirby (1: Kirby copies it as its base; 0: no ability), kirby_hat: own (its own hat / copy motions) / share,
             kirby_hat_dir (a folder to use as its copy hat model), kirby_scripts (1: Kirby's copy of it runs scripts
             of its own, copies of the base's copy scripts with its sounds / effects (1.4, default); 0: the base's),
             plate (the name plates' text; default the title), plate_lines (1 / 2; default as the game splits),
             font_plate / font_title / font_other (mincho / gothic / game / a .ttf file),
             title@REGION / subtitle@REGION (a language's own title, e.g. title@us_fr=Renard),
             voice@TONE (a WAV replacing that tone of its own banks, e.g. voice@snd_vc_Fox_Appeal01=a.wav)
  --portrait NAME:SET:NN=PNG              e.g. --portrait foxclone:chr_00:01=red.png  (NN empty for one-file sets)
  --stage SOURCE:NAME[:key=value,...]     e.g. --stage BattleField_f:CloneField:title=Clone Field,page=1
       keys: title, series, page (1 / 2), cosmetic, random (0: never picked by the random stage select)
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

INTS = {'costumes', 'series', 'sort_key', 'kind', 'ui_id', 'page', 'cosmetic', 'customs', 'fanfare', 'random',
        'own_sound', 'own_effects', 'kirby', 'kirby_scripts', 'plate_lines'}


def extras(opt):
    """the 1.3 keys of a --fighter into the spec's options"""
    for k in ('call', 'music'):
        v = opt.get(k)
        if v and v.lower().endswith('.wav'):
            opt[k + '_wav'] = v
            opt[k] = 'wav'
    for key in ('kirby', 'kirby_scripts'):
        if key in opt:
            opt[key] = bool(opt[key])
    if 'kirby_hat' in opt:
        opt['kirby_hat_mode'] = opt.pop('kirby_hat')
    if 'plate' in opt:
        opt['plate_text'] = opt.pop('plate')
    fonts = {}
    for t in ('plate', 'title', 'other'):
        if 'font_' + t in opt:
            fonts[t] = opt.pop('font_' + t)
    if fonts:
        opt['fonts'] = fonts
    titles, voices = {}, {}
    for k in list(opt):
        if '@' in k:
            what, where = k.split('@', 1)
            v = opt.pop(k)
            if what in ('title', 'subtitle'):
                titles.setdefault(where, {})[what] = v
            elif what == 'voice':
                voices[where] = v
    if titles:
        opt['titles'] = titles
    if voices:
        opt['voices'] = voices
    return opt


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
        if 'weapons' in opt and opt['weapons'] != 'all':
            opt['weapons'] = [w for w in opt['weapons'].split('+') if w and w != 'none']
        if 'customs' in opt:
            opt['customs'] = bool(opt['customs'])
        extras(opt)
        for k in ('fanfare', 'random', 'own_sound', 'own_effects'):
            if k in opt:
                opt[k] = bool(opt[k])
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
        if 'random' in opt:
            opt['random'] = bool(opt['random'])
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
    ap.add_argument('command', choices=['info', 'roster', 'check', 'build', 'css', 'sss', 'voices', 'plate'])
    ap.add_argument('--name')
    ap.add_argument('--replace', action='append')
    ap.add_argument('--import-folder')
    ap.add_argument('--text')
    ap.add_argument('--set', default='chrn_40')
    ap.add_argument('--font')
    ap.add_argument('--lines', type=int)
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
                                       ', the game\'s v288 executable' if info.get('v288') else
                                       ', the research base' if info['research_sha1'] else ''))
        for p in info.get('problems', []):
            print('  ' + p)
        for f in info['registry']['fighters']:
            print('  fighter clone %s kind 0x%X id %d from %s' % (f['name'], f['kind'], f['ui_id'], f['source']))
        for st in info['registry']['stages']:
            print('  stage clone %s cosmetic 0x%X from %s' % (st['name'], st['cosmetic'], st['source']))
        return
    if a.command == 'plate':
        from sm4shclonetool import plates as PL
        font = PL.resolve_font(a.font, 'plate', [a.data] if a.data else [])
        img, lines = PL.render(a.text or 'Clone', a.set, font, None, None, a.lines)
        img.save(a.png or 'plate.png')
        print('%s: %s (%s), font %s' % (a.png or 'plate.png', ' / '.join(lines), a.set, font))
        return
    s = Session(a.data, a.out or os.path.join(os.getcwd(), 'sm4shclonetool_out'), a.exe, a.ui, a.force)
    if a.command == 'voices':
        from sm4shclonetool import voices as V
        rec = next((f for f in s.reg['fighters'] if f['name'] == a.name), None)
        if rec is None:
            sys.exit('no clone %r in the project' % a.name)
        for r in a.replace or []:
            tone, wav = r.split('=', 1)
            hit = next((x for x in V.lines(rec, s.pkg_data) if tone in (x['name'], '%s:%d' % (x['file'], x['tone']))),
                       None)
            if hit is None:
                sys.exit('no tone %r in %s\'s banks' % (tone, a.name))
            V.replace(rec, s.pkg_data, hit['file'], hit['tone'], wav)
            print('replaced %s (%s) with %s' % (hit['name'], hit['file'], wav))
        if a.import_folder:
            for w, f, n in V.import_folder(rec, s.pkg_data, a.import_folder):
                print('replaced %s (%s) with %s' % (n, f, w))
        for x in V.lines(rec, s.pkg_data):
            print('%-10s %-40s %-36s %5.2f s' % (x['category'], x['name'], '%s:%d' % (x['file'], x['tone']),
                                                 x['seconds']))
        return
    if a.command == 'roster':
        for f in R.fighters(s.param_dirs(), s.reg):
            print('%3d %-14s kind 0x%02X %-12s sort %s%s' % (f['id'], f['ui_name'], f['kind'], f['name'],
                                                           f['sort'], ' (clone)' if f['clone'] else ''))
        print(s.limits_text())
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
        print(s.limits_text(reg))
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
