"""A cloning session: the creator's folders and executable, the registry, plan (check) and build (the package).

Folders (settings):
  data     the game's data folder as installed (vanilla or a mod): param/, ui/, fighter/, stage/, sound/
  ui       the UI folder the game shows (default: data/ui); a custom UI (its own portraits, chara.lm) goes here
  exe      the cross_f.rpx to patch (vanilla v288, or one this tool patched)
  out      the output / project folder: sm4shclonetool_project.json, INSTALL_TO_data/, INSTALL_TO_code/, README.txt

The package is cumulative: INSTALL_TO_data holds every file the project's clones changed or added (read back as the
newest copy of each file on the next build), so it installs over the creator's current data whether or not an
earlier package of the project was installed. Files equal to the data folder's are left out.
"""
import copy
import datetime
import hashlib
import os
import shutil

from . import _paths  # noqa: F401
from . import VERSION
from . import exe as X
from . import fighter as F
from . import preview as P
from . import roster as R
from . import stage as S
from .rpx import Rpx

CSB_TABLE = 0x10340F8C           # commonsoundtable.csb names (62, the executable's)


EXE_OUTPUTS = ('rpx', 'aroma', 'cemu')
EXE_OUTPUT_NAMES = {'rpx': 'patched cross_f.rpx', 'aroma': 'Aroma plugin patch file (console)',
                    'cemu': 'Cemu graphic pack'}
AROMA_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'aroma', 'sm4shclonetool.wps')
CEMU_PACK = 'Sm4shCloneTool_Clones'


def exe_outputs(value):
    """'rpx' / 'aroma' / 'cemu' / 'all' or a comma list -> a tuple of EXE_OUTPUTS (default the patched rpx)"""
    if not value:
        return ('rpx',)
    if isinstance(value, str):
        value = [v.strip().lower() for v in value.split(',') if v.strip()]
    out = []
    for v in value:
        for x in (EXE_OUTPUTS if v == 'all' else [v]):
            if x not in EXE_OUTPUTS:
                raise ValueError('unknown executable output %r (rpx, aroma, cemu or all)' % x)
            if x not in out:
                out.append(x)
    return tuple(out)


class Session:
    def __init__(self, data, out, exe=None, ui=None, force=False, log=print, exe_output=None):
        self.exe_output = exe_outputs(exe_output)
        self.data = os.path.abspath(data)
        self.ui = os.path.abspath(ui) if ui else os.path.join(self.data, 'ui')
        self.exe = os.path.abspath(exe) if exe else None
        self.out = os.path.abspath(out)
        self.force = force
        self.log = log
        self.proj = R.load_project(self.out)
        self.exe_info = None
        self.reg = self._registry()
        if self.exe and os.path.exists(self.exe):
            try:
                R.STAGE_NAMES = R.stage_kind_names(self.exe)
            except Exception:
                R.STAGE_NAMES = None

    # ------------------------------------------------------------ folders
    @property
    def pkg_data(self):
        return os.path.join(self.out, 'INSTALL_TO_data')

    @property
    def pkg_code(self):
        return os.path.join(self.out, 'INSTALL_TO_code')

    @property
    def pkg_sd(self):
        return os.path.join(self.out, 'INSTALL_TO_sd')

    @property
    def pkg_cemu(self):
        return os.path.join(self.out, 'INSTALL_TO_cemu')

    def param_dirs(self):
        return [os.path.join(self.pkg_data, 'param'), os.path.join(self.data, 'param')]

    def ui_dirs(self):
        return [os.path.join(self.pkg_data, 'ui'), self.ui, os.path.join(self.data, 'ui')]

    def _registry(self):
        reg = copy.deepcopy(self.proj.get('registry') or R.empty_registry())
        if self.exe and os.path.exists(self.exe):
            self.exe_info = X.inspect(self.exe)
            if self.exe_info['state'] == 'patched':
                ereg = self.exe_info['registry']
                if reg['fighters'] or reg['stages']:
                    names = lambda r: ([f['name'] for f in r['fighters']], [s['name'] for s in r['stages']])  # noqa
                    if names(reg) != names(ereg):
                        self.log('NOTE: the executable\'s clones %s differ from the project\'s %s: using the '
                                 'executable\'s' % (names(ereg), names(reg)))
                return copy.deepcopy(ereg)
        return reg

    # ------------------------------------------------------------ planning
    def articles(self, source, reg=None):
        """the base's articles (by the native base: a clone of a clone has its base's)"""
        if not self.exe:
            return []
        reg = reg or self.reg
        native = next((f['base'] for f in reg['fighters'] if f['name'] == source), source)
        try:
            return X.base_articles(self.exe, native)
        except Exception:
            return []

    def fighter_spec(self, source, name, cap=None, ui_name=None, title=None, **opt):
        kind, cid = F.next_slots(self.param_dirs(), self.reg)
        opt.setdefault('weapons', 'all')               # the "fully independent clone" preset
        opt.setdefault('own_sound', True)
        opt.setdefault('own_effects', True)
        spec = {'source': source, 'name': name, 'cap': cap or name.capitalize(),
                'ui_name': ui_name or (cap or name.capitalize()), 'title': title, 'kind': opt.pop('kind', None) or kind,
                'ui_id': opt.pop('ui_id', None) or cid}
        spec.update(opt)
        return spec

    def stage_spec(self, source, name, title=None, **opt):
        cos, _k = S.next_slots(self.reg)
        spec = {'source': source, 'name': name, 'title': title, 'cosmetic': opt.pop('cosmetic', None) or cos}
        spec.update(opt)
        return spec

    def plan(self, fighters=(), stages=()):
        """(registry with the new clones, records, errors, notes, file list, exe items) without writing"""
        reg = copy.deepcopy(self.reg)
        errors, notes, files, recs = [], [], [], []
        for spec in fighters:
            e = F.validate(spec, self.param_dirs(), self.ui_dirs(), reg)
            errors += ['%s: %s' % (spec['name'], x) for x in e]
            if e:
                continue
            if spec.get('weapons') == 'all':
                spec = dict(spec, weapons=self.articles(spec['source'], reg))
            rec = F.record(spec, reg)
            if rec.get('own_effects') and self.exe:
                missing = sorted(set(self.articles(spec['source'], reg)) - set(rec['weapons']))
                if missing:
                    notes.append('%s: own effect bank, but articles %s stay the base\'s: their effects only show with '
                                 'the base in the match (own every article for a fully independent clone)'
                                 % (rec['name'], ', '.join(missing)))
            if spec.get('after') is not None or spec.get('sort_key') is not None:
                keys, shift = F.sort_keys(self.param_dirs(), reg, spec.get('after'), spec.get('sort_key'))
                rec['sort'], rec['renumber'] = keys, shift
            reg['fighters'].append(rec)
            recs.append(('fighter', rec, spec))
            files += self._fighter_files(rec, spec)
        for spec in stages:
            e = S.validate(spec, self.param_dirs(), self.ui_dirs(), reg)
            errors += ['%s: %s' % (spec['name'], x) for x in e]
            if e:
                continue
            rec = S.record(spec, self.param_dirs(), reg)
            reg['stages'].append(rec)
            recs.append(('stage', rec, spec))
            files += self._stage_files(rec)
        if fighters:
            lim = self.limits(reg)
            if lim['css_entries'] > lim['css_capacity']:
                errors.append('the character select would show %d entries; its layout has places for %d (%s). '
                              'Use a UI whose lumen/chara/chara.lm has arrangements up to num_%03d'
                              % (lim['css_entries'], lim['css_capacity'], lim['css_source'], lim['css_entries']))
        for p in (1, 2):
            if stages and len(R.sss_pages(self.param_dirs(), reg)[p]) > S.PAGE_SLOTS:
                errors.append('stage select page %d would have %d stages; it has %d slots' % (
                    p, len(R.sss_pages(self.param_dirs(), reg)[p]), S.PAGE_SLOTS))
        wk = X.weapon_kinds(reg)
        for f in reg['fighters']:
            f['weapon_kinds'] = wk.get(f['name'], {})
        exe_items = []
        if self.exe:
            try:
                n, exe_items = X.plan(self.exe, reg, self.force)
                notes += n
            except X.ExeError as e:
                errors.append('executable: %s' % e)
            exe_items.append('output: %s' % ', '.join(EXE_OUTPUT_NAMES[o] for o in self.exe_output))
            if set(self.exe_output) - {'rpx'} and self.force and self.exe_info and \
                    self.exe_info.get('state') == 'modified':
                errors.append('executable: the Aroma / Cemu outputs patch the game\'s own v288 executable in memory; '
                              'they can\'t carry another mod\'s code ("patch anyway"): use the patched rpx output')
        else:
            notes.append('no executable given: only the data files are built (the clones need the patched '
                         'cross_f.rpx to load)')
        return reg, recs, errors, notes, files, exe_items

    def _fighter_files(self, rec, spec):
        n = rec['ui_name']
        out = ['param/fighter/fighter_param.bin (+ kind 0x%X)' % rec['kind'],
               'param/fighter/fighter_param_vl_%s.bin (copy of %s\'s)' % (rec['name'], rec['source']),
               'param/ai/fighter_ai_fighter_param.bin, fighter_ai_nfp_learning_param.bin',
               'param/simple/simple_character_db_cafe.bin, param/sound/audience_ouen_param.bin',
               'param/ui/ui_character_db.bin (+ id %d, sort %s)' % (rec['ui_id'], rec.get('sort') or 'after every entry'),
               'param/ui/ui_layout_db.bin, ui_skill_db.bin, ui_sound_call_voice_db.bin',
               'ui/message/melee.msbt (MmelChara*_%s)' % n,
               'ui/replace/chr/<set>/<set>_%s_NN.nut (portraits, new texture ids)' % n,
               'fighter/%s/ (copy of fighter/%s/, renamed; effect ids 0x3%02X -> 0x3%02X)'
               % (rec['name'], rec['source'], rec['source_kind'], rec['kind'])]
        if rec.get('weapons'):
            out.append('its own weapons: %s' % ', '.join(rec['weapons']))
        if rec.get('customs'):
            out.append('ui/message/menu.msbt, ui/replace/customize/spi_10/spi_10_%s_* (custom moves)' % n)
        if rec.get('fanfare', True):
            out.append('sound/config/bgm_fighter.fbb, commonsoundtable.csb (fanfare, KO voices)')
        return out

    def _stage_files(self, rec):
        return ['param/ui/ui_stage_db.bin (+ cosmetic 0x%X, kinds 0x%X / 0x%X, page %d)' % (
            rec['cosmetic'], rec['kind'], rec['kind'] + 1, rec['page']), 'param/ui/ui_sound_db.bin',
            'ui/message/melee.msbt (MmelStageN_ / MmelStageG_%s)' % rec['name'],
            'ui/replace/stage/<set>/<set>_%s.nut (icons)' % rec['name'],
            'stage/melee/%s/, stage/end/%s/ (copies of %s)' % (rec['name'], rec['name'], rec['source'])]

    def limits(self, reg=None):
        """how many clones fit, and why (docs: README "Limits")"""
        reg = reg or self.reg
        cap, src = P.css_capacity(self.ui_dirs())
        entries = len(R.css_entries(self.param_dirs(), reg))
        n = len(reg['fighters'])
        vanilla_entries = entries - sum(1 for f in reg['fighters'])
        pages = R.sss_pages(self.param_dirs(), reg)
        return {'fighters': n, 'fighters_max': min(F.MAX_CLONES, cap - vanilla_entries),
                'ids_max': F.MAX_CLONES, 'css_entries': entries, 'css_capacity': cap, 'css_source': src,
                'random': sum(1 for f in reg['fighters'] if f.get('random', True)),
                'stages': len(reg['stages']), 'page1': len(pages[1]), 'page2': len(pages[2]),
                'page_slots': S.PAGE_SLOTS,
                'stages_max': min(S.MAX_CLONES, 2 * S.PAGE_SLOTS - len([s for p in (1, 2) for s in pages[p]
                                                                         if not s['clone']]))}

    def limits_text(self, reg=None):
        m = self.limits(reg)
        return ('Fighter clones: %d of %d (character select: %d of %d places, %s; %d in the random select) | '
                'Stage clones: %d of %d (page 1: %d / %d, page 2: %d / %d)'
                % (m['fighters'], m['fighters_max'], m['css_entries'], m['css_capacity'], m['css_source'],
                   m['random'], m['stages'], m['stages_max'], m['page1'], m['page_slots'], m['page2'],
                   m['page_slots']))

    # ------------------------------------------------------------ build
    def build(self, fighters=(), stages=(), portraits=None, icons=None):
        """portraits: {fighter name: {(set, NN): png}}; icons: {stage name: {set: png}}. Returns a summary."""
        reg, recs, errors, notes, files, exe_items = self.plan(fighters, stages)
        if errors:
            raise X.ExeError('\n'.join(errors))
        for n in notes:
            self.log(n)
        os.makedirs(self.pkg_data, exist_ok=True)
        csb_names = None
        read = None
        if self.exe:
            x = Rpx(self.exe)
            csb_names = [x.cstr(x.r32(CSB_TABLE + 4 * i)) for i in range(62)]
            read = x.r32
        for what, rec, spec in recs:
            self.log('--- %s %s (from %s)' % (what, rec['name'], rec['source']))
            if what == 'fighter':
                F.build(rec, self.data, self.ui, self.pkg_data, reg, (portraits or {}).get(rec['name']), self.log,
                        rec.get('renumber', ()), csb_names, read)
            else:
                S.build(rec, self.data, self.ui, self.pkg_data, reg, (icons or {}).get(rec['name']), self.log)
        summary = {'clones': [r['name'] for _w, r, _s in recs]}
        if self.exe:
            summary.update(self._build_exe(reg))
        removed = self._prune()
        if removed:
            self.log('left out %d file(s) equal to the data folder\'s' % removed)
        for f in reg['fighters']:
            f.pop('renumber', None)
        self.reg = reg
        self.proj['registry'] = reg
        self.proj['settings'] = {'data': self.data, 'ui': self.ui, 'exe': self.exe, 'out': self.out}
        self.proj.setdefault('builds', []).append({'when': datetime.datetime.now().isoformat(timespec='seconds'),
                                                   'tool': VERSION, 'added': summary['clones']})
        R.save_project(self.out, self.proj)
        self.write_readme()
        summary['checks'] = self.check_package()
        for line in summary['checks']:
            self.log('check: ' + line)
        return summary

    def _build_exe(self, reg):
        """the executable outputs (exe_output): INSTALL_TO_code/cross_f.rpx, INSTALL_TO_sd/ (the Aroma plugin and its
        patch file), INSTALL_TO_cemu/ (a graphic pack); an output not chosen is removed from the package"""
        import shutil
        from . import patchset as PS
        out = {}
        dst = os.path.join(self.pkg_code, 'cross_f.rpx')
        if 'rpx' in self.exe_output:
            os.makedirs(self.pkg_code, exist_ok=True)
            tmp = dst + '.new'
            out['exe'] = X.build(self.exe, tmp, reg, self.force, self.log, work=self.out)
            os.replace(tmp, dst)
        elif os.path.isdir(self.pkg_code):
            shutil.rmtree(self.pkg_code)
        for o, d in (('aroma', self.pkg_sd), ('cemu', self.pkg_cemu)):
            if o not in self.exe_output and os.path.isdir(d):
                shutil.rmtree(d)
        if not set(self.exe_output) & {'aroma', 'cemu'}:
            return out
        ps = PS.export(self.exe, reg, self.log, work=self.out)
        out['patchset'] = {'sites': len(ps.sites), 'cave': ps.size, 'veneers': len(ps.veneers)}
        if 'aroma' in self.exe_output:
            pd = os.path.join(self.pkg_sd, 'wiiu', 'sm4shclonetool')
            if os.path.isdir(pd):
                shutil.rmtree(pd)
            os.makedirs(pd)
            blob = PS.plugin_bytes(ps)
            for t in PS.TITLE_IDS:
                open(os.path.join(pd, '%016X.patch' % t), 'wb').write(blob)
            plug = os.path.join(self.pkg_sd, 'wiiu', 'environments', 'aroma', 'plugins')
            if os.path.exists(AROMA_PLUGIN):
                os.makedirs(plug, exist_ok=True)
                shutil.copyfile(AROMA_PLUGIN, os.path.join(plug, 'sm4shclonetool.wps'))
            else:
                self.log('NOTE: the Aroma plugin (aroma/sm4shclonetool.wps) is not in this copy of the tool: build it '
                         'from aroma/ (README "The Aroma plugin")')
            self.log('Aroma: %s/<title id>.patch (%d bytes; %d game words, a %d KB cave)'
                     % (os.path.relpath(pd, self.out), len(blob), len(ps.sites), ps.size >> 10))
        if 'cemu' in self.exe_output:
            gd = os.path.join(self.pkg_cemu, 'graphicPacks', CEMU_PACK)
            os.makedirs(gd, exist_ok=True)
            hashes = [PS.V288_CEMU_HASH]
            if reg is not None and X.inspect(self.exe)['state'] == 'vanilla':
                h = PS.cemu_hash(self.exe)
                if h not in hashes:
                    hashes.append(h)
            text, _multi = PS.cemu_patches(ps, hashes)
            open(os.path.join(gd, 'patches.txt'), 'w', newline='\n').write(text)
            open(os.path.join(gd, 'rules.txt'), 'w', newline='\n').write(PS.cemu_rules(ps, CEMU_PACK))
            self.log('Cemu: %s (moduleMatches %s)' % (os.path.relpath(gd, self.out),
                                                       ', '.join('0x%08X' % h for h in hashes)))
        return out

    def _prune(self):
        from . import languages as L
        n = 0
        pairs = [(self.pkg_data, self.data)] + [(L.out_root(self.pkg_data, k), d)
                                                for k, d in L.region_dirs(self.data).items()]
        for pkg, data in pairs:
            if not os.path.isdir(pkg):
                continue
            for root, _d, fs in os.walk(pkg):
                for f in fs:
                    p = os.path.join(root, f)
                    rel = os.path.relpath(p, pkg)
                    q = os.path.join(data, rel)
                    if os.path.exists(q) and os.path.getsize(p) == os.path.getsize(q) and _same(p, q):
                        os.unlink(p)
                        n += 1
            for root, ds, fs in sorted(os.walk(pkg), reverse=True):
                if not os.listdir(root) and root != self.pkg_data:
                    os.rmdir(root)
        return n

    # ------------------------------------------------------------ checks after the build
    def check_package(self):
        out = []
        from . import textures as T
        ids = {}
        clash = []
        for root, _d, fs in os.walk(os.path.join(self.pkg_data, 'ui')):
            for f in fs:
                if f.endswith('.nut'):
                    p = os.path.join(root, f)
                    for _o, t in T.texture_ids(T.read_nut(p)):
                        if 'stage_13' in root:
                            continue
                        if t in ids and ids[t] != p:
                            clash.append('0x%08X: %s and %s' % (t, os.path.basename(ids[t]), f))
                        ids[t] = p
                    if T.decode(p) is None:
                        clash.append('%s does not decode' % f)
        own = set(ids)
        theirs = set()
        for d in (self.ui, os.path.join(self.data, 'ui')):
            if os.path.isdir(d):
                for root, _d, fs in os.walk(d):
                    for f in fs:
                        if f.endswith('.nut') and not os.path.exists(os.path.join(self.pkg_data, 'ui',
                                                                                 os.path.relpath(os.path.join(root, f), d))):
                            theirs |= {t for _o, t in T.texture_ids(T.read_nut(os.path.join(root, f)))}
        both = sorted(own & theirs)
        out.append('textures: %d new texture ids, %d clashes inside the package, %d with the UI folders%s' % (
            len(own), len(clash), len(both), (': ' + '; '.join(clash[:5])) if clash else ''))
        for f in self.reg['fighters']:
            d = os.path.join(self.pkg_data, 'fighter', f['name'])
            if os.path.isdir(d):
                have = {p for p in ('model/body/c00', 'script/animcmd/body', 'effect/%s' % f['name'])
                        if os.path.isdir(os.path.join(d, p))}
                out.append('fighter/%s/: %s' % (f['name'], ', '.join(sorted(have)) or 'no model / scripts / effects'))
        if self.exe and 'rpx' in self.exe_output:
            info = X.inspect(os.path.join(self.pkg_code, 'cross_f.rpx'))
            reg = info.get('registry') or {}
            out.append('executable: %s, %d fighter / %d stage clone(s) in its marker' % (
                info['state'], len(reg.get('fighters', [])), len(reg.get('stages', []))))
        if self.exe and 'aroma' in self.exe_output:
            from . import patchset as PS
            pd = os.path.join(self.pkg_sd, 'wiiu', 'sm4shclonetool')
            got = []
            for t in PS.TITLE_IDS:
                ps = PS.read_plugin(open(os.path.join(pd, '%016X.patch' % t), 'rb').read())
                got.append(t in ps.titles and ps.meta['fighters'] == [f['name'] for f in self.reg['fighters']])
            out.append('Aroma patch files: %d of %d read back (CRC, title, clones)%s' % (
                sum(got), len(got), '' if os.path.exists(os.path.join(self.pkg_sd, 'wiiu', 'environments', 'aroma',
                                                                       'plugins', 'sm4shclonetool.wps'))
                else '; the plugin itself is not in the package'))
        if self.exe and 'cemu' in self.exe_output:
            gd = os.path.join(self.pkg_cemu, 'graphicPacks', CEMU_PACK)
            out.append('Cemu graphic pack: %s' % ', '.join(f for f in ('rules.txt', 'patches.txt')
                                                          if os.path.exists(os.path.join(gd, f))))
        return out

    def write_readme(self):
        lines = ['Sm4shCloneTool %s package' % VERSION, '=' * 40, '',
                 'Built %s.' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '',
                 'INSTALL', '-------',
                 '1. Copy the contents of INSTALL_TO_data/ over your game\'s data folder (the files your mod',
                 '   manager / Sm4shExplorer installs into content/patch/data), keeping the folder layout.',
                 '   In Sm4shExplorer, set every packaged folder that gets a NEW file (ui/replace/chr/chr_*,',
                 '   ui/replace/stage/stage_*) to "Pack this folder" before rebuilding, or the game reads past the pack.',
                 '   INSTALL_TO_data(<region>)/ folders (if any) go over the matching data(<region>)/ folders: the',
                 '   clones\' names in that region\'s language.']
        n = 2
        if os.path.exists(os.path.join(self.pkg_code, 'cross_f.rpx')):
            lines += ['%d. Patched executable: replace code/cross_f.rpx with INSTALL_TO_code/cross_f.rpx (keep a copy of' % n,
                      '   your old one). It is your executable with the clone patch; the clones do not load without it.',
                      '   (Use ONE of the executable outputs: this, the Aroma plugin or the Cemu graphic pack.)']
            n += 1
        if os.path.isdir(os.path.join(self.pkg_sd, 'wiiu', 'sm4shclonetool')):
            lines += ['%d. Wii U with Aroma (the game\'s own, unmodified cross_f.rpx): copy the contents of INSTALL_TO_sd/' % n,
                      '   to the root of the SD card: wiiu/environments/aroma/plugins/sm4shclonetool.wps (the plugin)',
                      '   and wiiu/sm4shclonetool/<title id>.patch (this project\'s patch, one copy per region). At',
                      '   every start of Smash 4 v288 the plugin checks the game\'s words against the originals in the',
                      '   patch file and patches the game in memory; anything else and it patches nothing. Keep the',
                      '   game\'s own cross_f.rpx (do not also install a patched one). NOT YET TESTED ON A CONSOLE.']
            n += 1
        if os.path.isdir(os.path.join(self.pkg_cemu, 'graphicPacks')):
            lines += ['%d. Cemu (the game\'s own, unmodified cross_f.rpx): copy INSTALL_TO_cemu/graphicPacks/%s/ into' % (n, CEMU_PACK),
                      '   Cemu\'s graphicPacks folder, then enable it under Options > Graphic packs (Super Smash Bros.',
                      '   for Wii U > Mods). It patches the game in memory when it starts (moduleMatches = the v288',
                      '   executable\'s Cemu checksum). Not yet tested in Cemu: please report what you see.']
            n += 1
        lines += ['', 'CLONES', '------']
        for f in self.reg['fighters']:
            lines.append('fighter %-14s kind 0x%X, character id %d, UI name %s, from %s' % (
                f['name'], f['kind'], f['ui_id'], f['ui_name'], f['source']))
        for s in self.reg['stages']:
            lines.append('stage   %-14s cosmetic 0x%X, kinds 0x%X / 0x%X, page %d, from %s' % (
                s['name'], s['cosmetic'], s['kind'], s['kind'] + 1, s['page'], s['source']))
        lines += ['', 'The package holds every clone of this project (it is cumulative), only files that differ',
                  'from your data folder. Keep sm4shclonetool_project.json with it to add more clones later.']
        open(os.path.join(self.out, 'README.txt'), 'w').write('\n'.join(lines) + '\n')

    # ------------------------------------------------------------ previews
    def css(self, reg=None, highlight=(), out=None):
        return P.render_css(self.param_dirs(), self.ui_dirs(), reg or self.reg, highlight, out)

    def sss(self, reg=None, highlight=(), out=None):
        return P.render_sss(self.param_dirs(), self.ui_dirs(), reg or self.reg, highlight, out)


def _same(a, b):
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if x != y:
                return False
            if not x:
                return True
