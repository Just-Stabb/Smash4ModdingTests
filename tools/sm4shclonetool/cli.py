#!/usr/bin/env python3
"""Sm4shCloneTool, command line.

  python cli.py info    --exe cross_f.rpx                       what the executable is (vanilla / patched / other)
  python cli.py roster  --data DATA [--exe EXE] [--out OUT]     fighters and stages, with the clones
  python cli.py check   --data DATA --out OUT [--exe EXE] [--ui UI] CLONES...   validate, list the files and patches
  python cli.py build   --data DATA --out OUT [--exe EXE] [--ui UI] CLONES...   write the package
  python cli.py repair  --data DATA --out OUT [--exe EXE] [--ui UI]              rebuild a package a stopped build broke
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
  --exe-output rpx|aroma|cemu|all         what the executable patch is written as (a comma list for several):
       rpx (default): INSTALL_TO_code/cross_f.rpx, the patched executable;
       aroma: INSTALL_TO_sd/ for a Wii U with Aroma: the plugin (wiiu/environments/aroma/plugins/sm4shclonetool.wps)
              and the patch file it reads (wiiu/sm4shclonetool/<title id>.patch); the game's own cross_f.rpx stays;
       cemu: INSTALL_TO_cemu/graphicPacks/Sm4shCloneTool_Clones/ (rules.txt, patches.txt), a Cemu graphic pack
  python cli.py patchinfo --patch FILE.patch   what an Aroma patch file holds (and its checks)

IMPORTER (2.0): `import` adds animations, effects, sounds and articles to a fighter (a vanilla one by its folder name,
or a clone of the project) and rebuilds the package and the executable patch (check / build take the same options):
  --motion TARGET:NAME=FILE.omo[,copy=MOTION][,loop=0|1][,part=STEM@FILE.omo...]
       a new motion kind NAME playing FILE.omo (its index is printed); copy: a motion (its index 0x.., or its script
       name) whose four scripts, vl group 1 entry and flags the new one starts with (default: empty scripts)
  --effect TARGET:SOURCE:ENTRY[,name=SETNAME]      entry ENTRY of fighter SOURCE's effect bank (`effects --source`)
  --effect-file TARGET:FILE.efc:ENTRY[,name=..]    ... of any bank (its .ptcl beside it, model/ for its models)
  --sound TARGET:FILE.wav|FILE.idsp[,name=TONE][,alias=TEXT][,bank=se|vc|FILE][,volume=DB][,loop=1][,trim=0][,normalize=0]
  --article OWNER:NAME=SRC_OWNER/ARTICLE[,max=N]   a new article NAME of OWNER: a copy of SRC_OWNER's ARTICLE (its own
       weapon kind, files, effects, sounds), spawnable by its new article id (printed)
  python cli.py effects --data DATA --source FIGHTER   the entries of a fighter's effect bank (what --effect takes)
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


def _opts(text):
    out = {}
    for part in filter(None, (text or '').split(',')):
        k, _, v = part.partition('=')
        out[k.strip()] = v
    return out


def parse_imports(a):
    """the importer's options into importer.run items"""
    out = []
    for m in a.motion or []:
        tgt, rest = m.split(':', 1)
        head, _, opt = rest.partition(',')
        name, _, omo = head.partition('=')
        it = {'what': 'motion', 'target': tgt, 'name': name, 'omo': omo, 'parts': {}}
        for k, v in [kv.partition('=')[::2] for kv in filter(None, opt.split(','))]:
            if k == 'copy':
                it['copy'] = int(v, 0) if v[:1].isdigit() else v
            elif k == 'loop':
                it['loop'] = bool(int(v))
            elif k == 'part':
                stem, _, f = v.partition('@')
                it['parts'][stem] = f
        out.append(it)
    for e in a.effect or []:
        tgt, src, rest = e.split(':', 2)
        entry, _, opt = rest.partition(',')
        out.append(dict({'what': 'effect', 'target': tgt, 'source': src, 'entry': int(entry, 0)}, **_opts(opt)))
    for e in a.effect_file or []:
        tgt, rest = e.split(':', 1)
        path, _, rest = rest.rpartition(':')
        entry, _, opt = rest.partition(',')
        out.append(dict({'what': 'effect', 'target': tgt, 'efc': path, 'entry': int(entry, 0)}, **_opts(opt)))
    for e in a.sound or []:
        tgt, rest = e.split(':', 1)
        path, _, opt = rest.partition(',')
        it = dict({'what': 'sound', 'target': tgt, 'file': path}, **_opts(opt))
        for k in ('loop', 'trim', 'normalize'):
            if k in it:
                it[k] = bool(int(it[k]))
        if 'volume' in it:
            it['volume'] = float(it['volume'])
        out.append(it)
    for e in a.article or []:
        owner, rest = e.split(':', 1)
        head, _, opt = rest.partition(',')
        name, _, src = head.partition('=')
        so, _, sa = src.partition('/')
        it = dict({'what': 'article', 'owner': owner, 'target': owner, 'name': name, 'source_owner': so,
                   'source': sa}, **_opts(opt))
        if 'max' in it:
            it['max'] = int(it['max'])
        out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser(description='Sm4shCloneTool %s' % VERSION, epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'roster', 'check', 'build', 'css', 'sss', 'voices', 'plate',
                                        'patchinfo', 'repair', 'import', 'effects'])
    ap.add_argument('--motion', action='append')
    ap.add_argument('--effect', action='append')
    ap.add_argument('--effect-file', action='append')
    ap.add_argument('--sound', action='append')
    ap.add_argument('--article', action='append')
    ap.add_argument('--source')
    ap.add_argument('--exe-output', default='rpx')
    ap.add_argument('--patch')
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
    if a.command == 'patchinfo':
        from sm4shclonetool import patchset as PS
        ps = PS.read_plugin(open(a.patch, 'rb').read())
        print('%s: Sm4shCloneTool %s patch for v%d (titles %s): %d game words, a %d byte cave (%d relocated words); '
              'fighters %s, stages %s' % (a.patch, ps.meta.get('tool'), ps.version, ', '.join('%016X' % t for t in ps.titles),
                                          len(ps.sites), len(ps.blob), len(ps.cave_relocs),
                                          ', '.join(ps.meta.get('fighters', [])) or '-',
                                          ', '.join(ps.meta.get('stages', [])) or '-'))
        if a.exe:
            from sm4shclonetool.rpx import Rpx
            x = Rpx(a.exe)
            bad = [s_['addr'] for s_ in ps.sites if x.r32(s_['addr']) != s_['orig']]
            print('%s: %s' % (a.exe, 'every original word matches (the plugin would patch it)' if not bad else
                              '%d word(s) differ (first 0x%08X): the plugin would refuse' % (len(bad), bad[0])))
        return
    if a.command == 'plate':
        from sm4shclonetool import plates as PL
        font = PL.resolve_font(a.font, 'plate', [a.data] if a.data else [])
        img, lines = PL.render(a.text or 'Clone', a.set, font, None, None, a.lines)
        img.save(a.png or 'plate.png')
        print('%s: %s (%s), font %s' % (a.png or 'plate.png', ' / '.join(lines), a.set, font))
        return
    s = Session(a.data, a.out or os.path.join(os.getcwd(), 'sm4shclonetool_out'), a.exe, a.ui, a.force,
                exe_output=a.exe_output)
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
    if a.command == 'effects':
        from sm4shclonetool import importer as I
        efc, ptcl = I.effect_source({'source': a.source}, s.pkg_data, s.data)
        for i, st, model, fl in I.list_effects(efc, ptcl):
            print('%3d  %-40s %-34s flags 0x%X' % (i, st or '-', ('model ' + model) if model else '', fl))
        return
    if a.command == 'repair':
        problems = s.repair_problems()
        if problems:
            for p in problems:
                print('ERROR: ' + p)
            sys.exit(1)
        summary = s.repair()
        print('repaired: %s (%d clone file(s) kept, %d dropped)' % (s.out, summary['repair']['kept'],
                                                                     len(summary['repair']['dropped'])))
        return
    fighters, stages, portraits, icons = parse_clones(a, s)
    imports = parse_imports(a)
    if a.command == 'check':
        reg, recs, errors, notes, files, items = s.plan(fighters, stages, imports)
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
    if a.command == 'import' and not (imports or fighters or stages):
        sys.exit('import: give --motion / --effect / --effect-file / --sound / --article')
    if a.command in ('css', 'sss'):
        reg = s.plan(fighters, stages)[0]
        new = [f['ui_id'] for f in reg['fighters']] if a.command == 'css' else [x['cosmetic'] for x in reg['stages']]
        _img, info = (s.css if a.command == 'css' else s.sss)(reg, new, a.png or a.command + '.png')
        print(json.dumps({k: v for k, v in info.items() if k != 'slot'}, default=str)[:2000])
        return
    summary = s.build(fighters, stages, portraits, icons, imports)
    print('built: %s -> %s' % (', '.join(summary['clones']) or '(no new clone)', s.out))
    imp = summary.get('imported') or {}
    for t, n, i in imp.get('motions', []):
        print('motion  %s %s: motion kind 0x%X (%d)' % (t, n, i, i))
    for t, n, i in imp.get('effects', []):
        print('effect  %s %s: effect id 0x%08X' % (t, n, i))
    for t, n, i in imp.get('sounds', []):
        print('sound   %s %s: sound id 0x%08X' % (t, n, i))
    for x in imp.get('articles', []):
        print('article %s %s: article id %d, weapon kind 0x%X' % (x['owner'], x['name'], x['article_id'], x['kind']))


if __name__ == '__main__':
    main()
