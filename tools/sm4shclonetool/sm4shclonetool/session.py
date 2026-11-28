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
from . import rollback as RB
from . import stage as S
from .rpx import Rpx

REPAIR_OLD = '.sm4shclonetool_repair_old'
LEFTOVERS = ('is already in ui_character_db.bin', 'fighter_param.bin already has kind',
             'melee.msbt already has labels', 'is already in ui_stage_db.bin', 'melee.msbt already has')
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
        RB.recover(self.out, log)            # a build cut off (tool closed / crashed): the folder as it was before it
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

    # ------------------------------------------------------------ executable outputs
    def present_outputs(self):
        """the executable outputs the package already has (an earlier build made them)"""
        have = {'rpx': os.path.exists(os.path.join(self.pkg_code, 'cross_f.rpx')),
                'aroma': os.path.isdir(os.path.join(self.pkg_sd, 'wiiu', 'sm4shclonetool')),
                'cemu': os.path.isdir(os.path.join(self.pkg_cemu, 'graphicPacks', CEMU_PACK))}
        return tuple(o for o in EXE_OUTPUTS if have[o])

    def outputs(self):
        """(1.5.2) what a build writes: the chosen outputs and every one the package already has (each is made
        again, so none is left with an older set of clones; none is removed: delete its INSTALL_TO_* folder for that)"""
        want = set(self.exe_output) | set(self.present_outputs())
        return tuple(o for o in EXE_OUTPUTS if o in want)

    def rebuild_outputs(self):
        """(1.5.2) the project's clones written again for the chosen executable output (and the ones the package
        has), adding no clone: e.g. a project built for the SD card, later for Cemu or as a patched rpx"""
        if not self.reg['fighters'] and not self.reg['stages']:
            raise X.ExeError('the project has no clones yet: build one first')
        if not self.exe:
            raise X.ExeError('choose the executable (cross_f.rpx: the game\'s own, or one this tool patched)')
        return self.build([], [])

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
        if any(k in e for e in errors for k in LEFTOVERS):
            errors.append('the package has the kind / character id / labels of a clone the project does not list: '
                          'leftovers of a build that did not finish (before 1.5.1), or Data points at a folder the '
                          'package is installed in. Use "Repair package" (cli.py repair) to rebuild the package from '
                          'the project; the clones you have keep their files')
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
            kept = [o for o in self.outputs() if o not in self.exe_output]
            exe_items.append('output: %s%s' % (', '.join(EXE_OUTPUT_NAMES[o] for o in self.exe_output),
                                               ('; made again, already in the package: %s' % ', '.join(
                                                   EXE_OUTPUT_NAMES[o] for o in kept)) if kept else ''))
            if set(self.outputs()) - {'rpx'} and self.force and self.exe_info and \
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
        return self._transaction(lambda: self._write(reg, recs, portraits, icons))

    def _transaction(self, work):
        """work() runs with the project folder snapshotted: if it raises, the folder is put back as it was (nothing
        of an unfinished clone is left: no labels, parameter rows, kind or character id) and the error is raised"""
        try:
            with RB.Transaction(self.out, self.log):
                return work()
        except BaseException:
            self.proj = R.load_project(self.out)
            self.reg = self._registry()
            raise

    def _exe_reader(self):
        if not self.exe:
            return None, None
        x = Rpx(self.exe)
        return [x.cstr(x.r32(CSB_TABLE + 4 * i)) for i in range(62)], x.r32

    def _build_rec(self, what, rec, reg, portraits, icons, csb_names, read):
        self.log('--- %s %s (from %s)' % (what, rec['name'], rec['source']))
        if what == 'fighter':
            F.build(rec, self.data, self.ui, self.pkg_data, reg, (portraits or {}).get(rec['name']), self.log,
                    rec.get('renumber', ()), csb_names, read)
        else:
            S.build(rec, self.data, self.ui, self.pkg_data, reg, (icons or {}).get(rec['name']), self.log)

    def _write(self, reg, recs, portraits, icons):
        os.makedirs(self.pkg_data, exist_ok=True)
        csb_names, read = self._exe_reader()
        for what, rec, spec in recs:
            self._build_rec(what, rec, reg, portraits, icons, csb_names, read)
        summary = {'clones': [r['name'] for _w, r, _s in recs]}
        return self._finish(reg, summary, {'added': summary['clones']})

    def _finish(self, reg, summary, build_entry):
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
        entry = {'when': datetime.datetime.now().isoformat(timespec='seconds'), 'tool': VERSION}
        entry.update(build_entry)
        self.proj.setdefault('builds', []).append(entry)
        R.save_project(self.out, self.proj)
        self.write_readme()
        summary['checks'] = self.check_package()
        for line in summary['checks']:
            self.log('check: ' + line)
        return summary

    # ------------------------------------------------------------ repair
    def repair_problems(self, reg=None):
        """[reasons the package can't be rebuilt from the project] (empty: repair() can run)"""
        reg = reg or self.reg
        out = []
        if not reg['fighters'] and not reg['stages']:
            out.append('the project has no clones (nothing to rebuild: delete the INSTALL_TO_* folders to start over)')
        dp = [os.path.join(self.data, 'param')]
        g, _ = R.load_db(dp, 'fighter/fighter_param.bin')
        if g is not None and any(e[0][1] >= 0x41 for e in g[2]):
            out.append('the data folder already has new fighter kinds (a package is installed in it): set Data to '
                       'your data folder without this project\'s package')
        g, _ = R.load_db(dp, 'ui/ui_character_db.bin')
        if g is not None and any(59 <= e[0][1] < 200 for e in g[2]):
            out.append('the data folder already has new character ids (a package is installed in it): set Data to '
                       'your data folder without this project\'s package')
        missing = sorted({p for f in reg['fighters'] for p in _paths_in(f) if not os.path.exists(p)})
        out += ['%s (a file the clones were built with) is missing: put it back, or remove it from the clone in '
                'the project file' % p for p in missing]
        return out

    def _batches(self, reg):
        """the clones in the builds that added them (the character select order depends on which clones were
        placed in one build): [[('fighter' | 'stage', rec)]]"""
        names = {f['name']: ('fighter', f) for f in reg['fighters']}
        names.update({s['name']: ('stage', s) for s in reg['stages']})
        order = [f['name'] for f in reg['fighters']] + [s['name'] for s in reg['stages']]
        seen, batches = set(), []
        for b in self.proj.get('builds', []):
            got = [n for n in b.get('added', []) if n in names and n not in seen]
            if got:
                seen |= set(got)
                batches.append(sorted(got, key=order.index))
        batches += [[n] for n in order if n not in seen]
        return [[names[n] for n in b] for b in batches]

    def _stray_names(self, old, reg):
        """the names (internal / Cap / UI) of clones the broken package has and the project doesn't list: from
        melee.msbt's labels and the fighter / stage folders that are in neither the data folder nor the project"""
        import re
        import msbt
        mine = {x.lower() for f in reg['fighters'] for x in (f['name'], f['cap'], f['ui_name'])}
        mine |= {st['name'].lower() for st in reg['stages']}
        out = set()
        pkg = os.path.join(old, 'INSTALL_TO_data')
        mp = os.path.join(pkg, 'ui', 'message', 'melee.msbt')
        dp = R.first([self.ui, os.path.join(self.data, 'ui')], 'message/melee.msbt')
        if os.path.exists(mp):
            have = set(msbt.Msbt(open(dp, 'rb').read()).labels) if dp else set()
            for lab in msbt.Msbt(open(mp, 'rb').read()).labels:
                if lab in have:
                    continue
                m = re.match(r'^MmelChara\w*?_\d+_(\w+)$', lab) or re.match(r'^MmelStage[A-Z]_(\w+)$', lab)
                if m and m.group(1).lower() not in mine:
                    out.add(m.group(1))
        for sub in ('fighter', os.path.join('stage', 'melee'), os.path.join('stage', 'end')):
            d = os.path.join(pkg, sub)
            if not os.path.isdir(d):
                continue
            for n in os.listdir(d):
                if n.lower() in mine or os.path.exists(os.path.join(self.data, sub, n)):
                    continue
                out.add(n)
                snd = os.path.join(d, n, 'sound')
                if os.path.isdir(snd):
                    for f in os.listdir(snd):
                        m = re.match(r'^snd_(?:se|vc)_(\w+?)(?:_\w+)?\.nus3bank$', f)
                        if m and m.group(1).lower() not in mine:
                            out.add(m.group(1))
        return out

    def repair(self):
        """rebuilds the package from the project's clone list, for a package left broken (e.g. by a build that
        stopped part way before 1.5.1: the next kind / character id / labels taken by a clone the project doesn't
        list). The shared files (parameters, labels, databases, sound tables, Kirby's files) are made again from
        the data folder; each listed clone's own files (its fighter / stage folders, portraits, icons, plates,
        sounds, also any edits made to them in the package) are kept as they were; what belongs to no listed clone
        is dropped. Returns a summary (rebuilt / kept / dropped files)."""
        reg = copy.deepcopy(self.reg)
        problems = self.repair_problems(reg)
        if problems:
            raise X.ExeError('\n'.join(problems))
        wk = X.weapon_kinds(reg)
        for f in reg['fighters']:
            f['weapon_kinds'] = wk.get(f['name'], f.get('weapon_kinds', {}))
        return self._transaction(lambda: self._repair(reg))

    def _repair(self, reg):
        from . import languages as L
        from .kirby_copy import NAMES_FILE
        old = os.path.join(self.out, REPAIR_OLD)
        if os.path.exists(old):
            shutil.rmtree(old)
        os.makedirs(old)
        moved = [n for n in os.listdir(self.out) if n.startswith('INSTALL_TO_data') or n == NAMES_FILE]
        for n in moved:
            os.replace(os.path.join(self.out, n), os.path.join(old, n))
        self.log('=== repair: rebuilding the package of %d fighter / %d stage clone(s) from the project'
                 % (len(reg['fighters']), len(reg['stages'])))
        os.makedirs(self.pkg_data, exist_ok=True)
        csb_names, read = self._exe_reader()
        for batch in self._batches(reg):
            for what, rec in batch:               # the shifts the build placing them computed (before the batch)
                if what == 'fighter' and rec.get('sort'):
                    g, _ = R.load_db(self.param_dirs(), 'ui/ui_character_db.bin')
                    rec['renumber'] = [e[0][1] for e in g[2] if e[0][1] < 200 and e[0][1] != rec['ui_id']
                                       and e[13][1] >= rec['sort'][0]]
            for what, rec in batch:
                self._build_rec(what, rec, reg, None, None, csb_names, read)
            for what, rec in batch:
                rec.pop('renumber', None)             # (as the next build found them)
        # each clone's own files (new files, not the data folder's) as they were in the package
        roots = {'INSTALL_TO_data': self.data}
        for k, d in L.region_dirs(self.data).items():
            roots[os.path.basename(L.out_root(self.pkg_data, k))] = d
        strays = self._stray_names(old, reg)
        if strays:
            self.log('repair: the unfinished clone(s) in the package: %s' % ', '.join(sorted(strays)))
        kept, dropped, rebuilt = [], [], []
        for top in moved:
            src_top = os.path.join(old, top)
            if not os.path.isdir(src_top):
                continue
            for root, _d, fs in os.walk(src_top):
                for fn in fs:
                    p = os.path.join(root, fn)
                    rel = os.path.relpath(p, src_top)
                    dst = os.path.join(self.out, top, rel)
                    data_root = roots.get(top)
                    shared = data_root is not None and os.path.exists(os.path.join(data_root, rel))
                    if shared:
                        if os.path.exists(dst) and not _same(p, dst):
                            rebuilt.append(os.path.join(top, rel))
                    elif os.path.exists(dst) or not _names_any(os.path.join(top, rel), strays):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        os.replace(p, dst)               # a listed clone's own file (or one of yours), as it was
                        kept.append(os.path.join(top, rel))
                    else:
                        dropped.append(os.path.join(top, rel))
        shutil.rmtree(old)
        for x in dropped:
            self.log('dropped (no clone of the project has it): %s' % x)
        self.log('repair: shared files made again (%d differed from the broken package), %d clone file(s) kept, %d '
                 'dropped' % (len(rebuilt), len(kept), len(dropped)))
        summary = {'clones': [], 'repair': {'rebuilt': rebuilt, 'kept': len(kept), 'dropped': dropped}}
        return self._finish(reg, summary, {'added': [], 'repair': True})

    def _build_exe(self, reg):
        """the executable outputs (outputs(): the chosen ones and those the package has): INSTALL_TO_code/cross_f.rpx,
        INSTALL_TO_sd/ (the Aroma plugin and its patch file), INSTALL_TO_cemu/ (a graphic pack). None is removed (the
        executable read may be the package's own cross_f.rpx)"""
        import shutil
        from . import patchset as PS
        out = {}
        outs = self.outputs()
        kept = [o for o in outs if o not in self.exe_output]
        if kept:
            self.log('also made again (already in the package): %s' % ', '.join(EXE_OUTPUT_NAMES[o] for o in kept))
        dst = os.path.join(self.pkg_code, 'cross_f.rpx')
        if 'rpx' in outs:
            os.makedirs(self.pkg_code, exist_ok=True)
            tmp = dst + '.new'
            out['exe'] = X.build(self.exe, tmp, reg, self.force, self.log, work=self.out)
            os.replace(tmp, dst)
        if not set(outs) & {'aroma', 'cemu'}:
            return out
        ps = PS.export(self.exe, reg, self.log, work=self.out)
        out['patchset'] = {'sites': len(ps.sites), 'cave': ps.size, 'veneers': len(ps.veneers)}
        if 'aroma' in outs:
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
        if 'cemu' in outs:
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
        if self.exe and 'rpx' in self.outputs():
            info = X.inspect(os.path.join(self.pkg_code, 'cross_f.rpx'))
            reg = info.get('registry') or {}
            out.append('executable: %s, %d fighter / %d stage clone(s) in its marker' % (
                info['state'], len(reg.get('fighters', [])), len(reg.get('stages', []))))
        if self.exe and 'aroma' in self.outputs():
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
        if self.exe and 'cemu' in self.outputs():
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


def _names_any(rel, names):
    """rel names one of names (a whole folder name, or a part of a file name between _ . - )"""
    import re
    parts = {x.lower() for x in re.split(r'[\\/_.\-]', rel) if x}
    return any(n.lower() in parts for n in names)


def _paths_in(rec):
    """the files a clone record names (WAVs, fonts, a Kirby hat folder): absolute paths"""
    out = []

    def go(v):
        if isinstance(v, str):
            if os.path.isabs(v):
                out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                go(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                go(x)
    for k in ('call_wav', 'music_wav', 'voices', 'fonts', 'kirby_hat_dir'):
        go(rec.get(k))
    return out


def _same(a, b):
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if x != y:
                return False
            if not x:
                return True
