#!/usr/bin/env python3
"""Sm4shCloneTool: the window (Tkinter). Pick a base fighter or stage, name the clone, choose its options and
portraits, see where it lands on the character / stage select, then Check and Build the package.

  python gui.py [--data DATA] [--ui UI] [--exe EXE] [--out OUT] [--screenshot FILE.png [--tab fighters|stages]]
"""
import argparse
import base64
import io
import json
import os
import queue
import subprocess
import sys
import threading
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tkinter as tk  # noqa: E402
from tkinter import filedialog, messagebox, ttk  # noqa: E402

from sm4shclonetool import VERSION  # noqa: E402
from sm4shclonetool import roster as R  # noqa: E402
from sm4shclonetool import preview as P  # noqa: E402
from sm4shclonetool import textures as T  # noqa: E402
from sm4shclonetool.fighter import PORTRAIT_SETS  # noqa: E402
from sm4shclonetool.session import Session  # noqa: E402

TITLE = 'Sm4shCloneTool %s' % VERSION
SETTINGS = os.path.join(os.path.expanduser('~'), '.sm4shclonetool.json')
ICON = 48
ICON_SETS = ['chr_10', 'chr_00', 'stock_90', 'chr_13']


def photo(img, size=None):
    """a PIL image as a Tk PhotoImage (PNG data: no ImageTk needed)"""
    if size:
        img = img.copy()
        img.thumbnail(size)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))


def load_settings():
    try:
        return json.load(open(SETTINGS))
    except Exception:
        return {}


def save_settings(s):
    try:
        json.dump(s, open(SETTINGS, 'w'), indent=1)
    except Exception:
        pass


class App:
    def __init__(self, root, args):
        self.root = root
        root.title(TITLE)
        root.geometry('1480x960')
        self.q = queue.Queue()
        self.session = None
        self.images = []
        self.pending_f, self.pending_s = [], []
        self.portraits, self.icons = {}, {}
        st = load_settings()
        self.vars = {k: tk.StringVar(value=getattr(args, k, None) or st.get(k, '')) for k in ('data', 'ui', 'exe', 'out')}
        self.force = tk.BooleanVar(value=False)
        self._folders()
        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=6, pady=4)
        self.nb = nb
        self.ftab, self.stab = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(self.ftab, text='Fighters')
        nb.add(self.stab, text='Stages')
        self._fighter_tab()
        self._stage_tab()
        self._bottom()
        root.after(100, self._poll)
        if all(self.vars[k].get() for k in ('data', 'out')):
            root.after(200, self.reload)

    # ------------------------------------------------------------ layout
    def _folders(self):
        f = ttk.LabelFrame(self.root, text='Folders (remembered)')
        f.pack(fill='x', padx=6, pady=4)
        rows = [('data', 'Game data folder (param/, ui/, fighter/, stage/, sound/)', True),
                ('ui', 'Custom UI folder (optional; default data/ui)', True),
                ('exe', 'Current cross_f.rpx (vanilla, or patched by this tool)', False),
                ('out', 'Output / project folder', True)]
        for i, (k, label, is_dir) in enumerate(rows):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky='w', padx=4)
            ttk.Entry(f, textvariable=self.vars[k], width=70).grid(row=i, column=1, sticky='we', padx=4)
            ttk.Button(f, text='Browse...', command=lambda k=k, d=is_dir: self._browse(k, d)).grid(row=i, column=2)
        ttk.Checkbutton(f, text='Patch anyway (executable with another mod\'s code space)', variable=self.force).grid(
            row=0, column=3, padx=8)
        ttk.Button(f, text='Load / refresh', command=self.reload).grid(row=1, column=3, padx=8)
        self.exe_state = ttk.Label(f, text='', foreground='#205080')
        self.exe_state.grid(row=2, column=3, rowspan=2, padx=8, sticky='w')
        f.columnconfigure(1, weight=1)

    def _browse(self, k, is_dir):
        p = filedialog.askdirectory() if is_dir else filedialog.askopenfilename(
            filetypes=[('cross_f.rpx', '*.rpx'), ('all', '*.*')])
        if p:
            self.vars[k].set(p)

    def _roster_panel(self, parent, title):
        lf = ttk.LabelFrame(parent, text=title)
        canvas = tk.Canvas(lf, width=330, background='#1e2433', highlightthickness=0)
        sb = ttk.Scrollbar(lf, orient='vertical', command=canvas.yview)
        inner = tk.Frame(canvas, background='#1e2433')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='y')
        sb.pack(side='left', fill='y')
        return lf, inner

    def _fighter_tab(self):
        t = self.ftab
        lf, self.f_grid = self._roster_panel(t, 'Base fighter (click one)')
        lf.pack(side='left', fill='y', padx=4, pady=4)
        mid = ttk.Frame(t)
        mid.pack(side='left', fill='y', padx=4)
        form = ttk.LabelFrame(mid, text='Clone')
        form.pack(fill='x')
        self.fv = {}
        fields = [('source', 'Base fighter'), ('name', 'Internal name (lowercase)'), ('cap', 'Cap name (files)'),
                  ('ui_name', 'UI name (portraits / labels)'), ('title', 'Title (shown name)'),
                  ('subtitle', 'Subtitle (CSS line)'), ('series', 'Series icon id'), ('costumes', 'Costumes'),
                  ('kind', 'Fighter kind (auto)'), ('ui_id', 'Character id (auto)'),
                  ('after', 'CSS: place after (name / id)'), ('sort_key', 'CSS: or first sort key')]
        for i, (k, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky='w', padx=3, pady=1)
            v = tk.StringVar()
            self.fv[k] = v
            ttk.Entry(form, textvariable=v, width=26).grid(row=i, column=1, padx=3, pady=1)
            v.trace_add('write', lambda *_: self._schedule_preview())
        self.fv['name'].trace_add('write', self._auto_names)
        opt = ttk.LabelFrame(mid, text='Options')
        opt.pack(fill='x', pady=4)
        self.customs = tk.BooleanVar(value=True)
        self.fanfare = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='Custom moves (owns the base\'s; menu labels / icons)', variable=self.customs).pack(anchor='w')
        ttk.Checkbutton(opt, text='Victory fanfare and KO voices (sound config records)', variable=self.fanfare).pack(anchor='w')
        ttk.Label(opt, text='Own articles (weapon kinds) - the base\'s articles:').pack(anchor='w')
        self.weapons = tk.Listbox(opt, selectmode='multiple', height=3, exportselection=False)
        self.weapons.pack(fill='x')
        ttk.Label(opt, text='Kirby: vanilla Kirby can\'t copy new kinds (no copy ability).', foreground='#806020').pack(anchor='w')
        pf = ttk.LabelFrame(mid, text='Portraits (default: the base\'s, new texture ids)')
        pf.pack(fill='x', pady=4)
        self.p_set = ttk.Combobox(pf, values=PORTRAIT_SETS, width=9, state='readonly')
        self.p_set.set('chr_00')
        self.p_set.grid(row=0, column=0)
        self.p_nn = ttk.Combobox(pf, values=['%02d' % i for i in range(1, 17)] + [''], width=4)
        self.p_nn.set('01')
        self.p_nn.grid(row=0, column=1)
        ttk.Button(pf, text='Import PNG...', command=self._import_portrait).grid(row=0, column=2)
        ttk.Button(pf, text='Clear', command=self._clear_portraits).grid(row=0, column=3)
        self.p_list = tk.Listbox(pf, height=3, width=46)
        self.p_list.grid(row=1, column=0, columnspan=4, sticky='we')
        bf = ttk.Frame(mid)
        bf.pack(fill='x', pady=4)
        ttk.Button(bf, text='Add to plan', command=self._add_fighter).pack(side='left')
        ttk.Button(bf, text='Remove from plan', command=self._remove_pending).pack(side='left', padx=4)
        right = ttk.LabelFrame(t, text='Character select preview (your UI; the clone highlighted)')
        right.pack(side='left', fill='both', expand=True, padx=4, pady=4)
        self.css_label = tk.Label(right, background='#202840')
        self.css_label.pack(fill='both', expand=True)
        self.css_info = ttk.Label(right, text='', wraplength=820)
        self.css_info.pack(fill='x')

    def _stage_tab(self):
        t = self.stab
        lf, self.s_grid = self._roster_panel(t, 'Base stage (click one)')
        lf.pack(side='left', fill='y', padx=4, pady=4)
        mid = ttk.Frame(t)
        mid.pack(side='left', fill='y', padx=4)
        form = ttk.LabelFrame(mid, text='Stage clone')
        form.pack(fill='x')
        self.sv = {}
        for i, (k, label) in enumerate([('source', 'Base stage'), ('name', 'Folder name (e.g. CloneField)'),
                                        ('title', 'Title (shown name)'), ('series', 'Series line'),
                                        ('page', 'Stage select page (1 / 2)'), ('cosmetic', 'Cosmetic id (auto)')]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky='w', padx=3, pady=1)
            v = tk.StringVar(value='1' if k == 'page' else '')
            self.sv[k] = v
            ttk.Entry(form, textvariable=v, width=26).grid(row=i, column=1, padx=3, pady=1)
            v.trace_add('write', lambda *_: self._schedule_preview())
        pf = ttk.LabelFrame(mid, text='Stage icons (default: the base\'s, new texture ids)')
        pf.pack(fill='x', pady=4)
        self.i_set = ttk.Combobox(pf, values=['stage_00', 'stage_10', 'stage_11', 'stage_12', 'stage_13', 'stage_30',
                                              'stage_31', 'stage_32', 'stage_40', 'stage_41'], width=10, state='readonly')
        self.i_set.set('stage_10')
        self.i_set.grid(row=0, column=0)
        ttk.Button(pf, text='Import PNG...', command=self._import_icon).grid(row=0, column=1)
        self.i_list = tk.Listbox(pf, height=4, width=46)
        self.i_list.grid(row=1, column=0, columnspan=3)
        bf = ttk.Frame(mid)
        bf.pack(fill='x', pady=4)
        ttk.Button(bf, text='Add to plan', command=self._add_stage).pack(side='left')
        right = ttk.LabelFrame(t, text='Stage select preview (the clone highlighted)')
        right.pack(side='left', fill='both', expand=True, padx=4, pady=4)
        self.sss_label = tk.Label(right, background='#203028')
        self.sss_label.pack(fill='both', expand=True)

    def _bottom(self):
        f = ttk.Frame(self.root)
        f.pack(fill='both', padx=6, pady=4)
        left = ttk.Frame(f)
        left.pack(side='left', fill='y')
        ttk.Label(left, text='Plan (built together):').pack(anchor='w')
        self.plan_list = tk.Listbox(left, height=5, width=48)
        self.plan_list.pack()
        btn = ttk.Frame(left)
        btn.pack(fill='x', pady=4)
        ttk.Button(btn, text='Check', command=self.check).pack(side='left')
        ttk.Button(btn, text='Build', command=self.build).pack(side='left', padx=4)
        ttk.Button(btn, text='Open output', command=self.open_output).pack(side='left')
        self.log = tk.Text(f, height=10, wrap='word', background='#10141c', foreground='#d8e0f0')
        self.log.pack(side='left', fill='both', expand=True, padx=6)

    # ------------------------------------------------------------ data
    def say(self, text):
        self.q.put(text)

    def _poll(self):
        try:
            while True:
                line = self.q.get_nowait()
                self.log.insert('end', line + '\n')
                self.log.see('end')
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def reload(self):
        s = {k: v.get() for k, v in self.vars.items()}
        save_settings(s)
        if not s['data'] or not s['out']:
            messagebox.showinfo(TITLE, 'Choose the game data folder and an output folder first.')
            return
        try:
            self.session = Session(s['data'], s['out'], s['exe'] or None, s['ui'] or None, self.force.get(), self.say)
        except Exception as e:
            self.say('ERROR: %s' % e)
            return
        info = self.session.exe_info
        if info:
            txt = {'vanilla': 'Executable: vanilla (ready to patch)',
                   'patched': 'Executable: patched by Sm4shCloneTool (%d fighter / %d stage clones)' % (
                       len(info['registry']['fighters']), len(info['registry']['stages'])),
                   'modified': 'Executable: NOT vanilla - ' + '; '.join(info.get('problems', []))}[info['state']]
        else:
            txt = 'No executable: data files only'
        self.exe_state.configure(text=txt)
        self.say(txt)
        self._fill_fighters()
        self._fill_stages()
        self._schedule_preview()

    def _fill_fighters(self):
        for w in self.f_grid.winfo_children():
            w.destroy()
        s = self.session
        fs = R.base_choices(s.param_dirs(), s.reg)
        self.f_icons = []
        for i, f in enumerate(fs):
            p = T.find_icon(s.ui_dirs(), ICON_SETS, f['ui_name'])
            img = T.decode(p) if p else None
            kw = {}
            if img is not None:
                ph = photo(img, (ICON, ICON))
                self.f_icons.append(ph)
                kw['image'] = ph
                kw['compound'] = 'top'
            b = tk.Button(self.f_grid, text=f['ui_name'] + (' *' if f['clone'] else ''), width=ICON + 8 if kw else 9,
                          height=ICON + 18 if kw else 3, font=('TkDefaultFont', 7), background='#2c3550',
                          foreground='white', relief='flat', command=lambda f=f: self._pick_fighter(f), **kw)
            b.grid(row=i // 4, column=i % 4, padx=2, pady=2)
        self.f_count = len(fs)
        self.f_icon_count = len(self.f_icons)
        self.say('roster: %d fighters (%d with an icon from your UI), %d clone(s) so far'
                 % (len(fs), len(self.f_icons), len(s.reg['fighters'])))

    def _fill_stages(self):
        for w in self.s_grid.winfo_children():
            w.destroy()
        s = self.session
        try:
            ss = R.stages(s.param_dirs(), s.reg)
        except Exception as e:
            self.say('stages: %s' % e)
            return
        self.s_icons = []
        
        for i, x in enumerate(ss):
            p = T.find_icon(s.ui_dirs(), ['stage_10', 'stage_00'], x['name'])
            img = T.decode(p) if p else None
            kw = {}
            if img is not None:
                ph = photo(img, (ICON * 2, ICON))
                self.s_icons.append(ph)
                kw = {'image': ph, 'compound': 'top'}
            b = tk.Button(self.s_grid, text=x['name'], font=('TkDefaultFont', 7), background='#2c4a40',
                          foreground='white', relief='flat', width=ICON * 2 if kw else 14, height=ICON + 16 if kw else 2,
                          command=lambda x=x: self._pick_stage(x), **kw)
            b.grid(row=i // 2, column=i % 2, padx=2, pady=2)

    def _pick_fighter(self, f):
        self.fv['source'].set(f['name'])
        s = self.session
        kind, cid = 0x41 + len(s.reg['fighters']) + len(self.pending_f), 59 + len(s.reg['fighters']) + len(self.pending_f)
        self.fv['kind'].set('0x%X' % kind)
        self.fv['ui_id'].set(str(cid))
        self.fv['costumes'].set(str(f['costumes']))
        self.fv['series'].set(str(f['series']))
        self.fv['after'].set(f['ui_name'])
        if not self.fv['name'].get():
            self.fv['name'].set(f['name'] + 'clone')
        self.weapons.delete(0, 'end')
        d = R.first([os.path.join(s.pkg_data, 'fighter', f['name'], 'model'),
                     os.path.join(s.data, 'fighter', f['name'], 'model')], '')
        if d and os.path.isdir(d):
            for a in sorted(os.listdir(d)):
                if a != 'body' and os.path.isdir(os.path.join(d, a)):
                    self.weapons.insert('end', a)

    def _auto_names(self, *_):
        n = self.fv['name'].get()
        if n:
            last = getattr(self, '_last_auto', '')
            for k in ('cap', 'ui_name', 'title'):
                if not self.fv[k].get() or self.fv[k].get() == last:
                    self.fv[k].set(n.capitalize())
            self._last_auto = n.capitalize()

    def _pick_stage(self, x):
        self.sv['source'].set(x['name'])
        if not self.sv['name'].get():
            self.sv['name'].set('Clone' + x['name'].split('_')[0])
        self.sv['cosmetic'].set('0x%X' % (0x38 + len(self.session.reg['stages']) + len(self.pending_s)))

    def _import_portrait(self):
        p = filedialog.askopenfilename(filetypes=[('PNG', '*.png')])
        if p:
            name = self.fv['name'].get() or 'clone'
            self.portraits.setdefault(name, {})[(self.p_set.get(), self.p_nn.get())] = p
            self._list_portraits()

    def _clear_portraits(self):
        self.portraits.pop(self.fv['name'].get(), None)
        self._list_portraits()

    def _list_portraits(self):
        self.p_list.delete(0, 'end')
        for (st, nn), p in sorted(self.portraits.get(self.fv['name'].get(), {}).items()):
            self.p_list.insert('end', '%s %s <- %s' % (st, nn or '-', os.path.basename(p)))

    def _import_icon(self):
        p = filedialog.askopenfilename(filetypes=[('PNG', '*.png')])
        if p:
            self.icons.setdefault(self.sv['name'].get(), {})[self.i_set.get()] = p
            self.i_list.delete(0, 'end')
            for st, q in sorted(self.icons.get(self.sv['name'].get(), {}).items()):
                self.i_list.insert('end', '%s <- %s' % (st, os.path.basename(q)))

    # ------------------------------------------------------------ specs
    def fighter_spec(self):
        v = {k: x.get().strip() for k, x in self.fv.items()}
        if not (v['source'] and v['name']):
            return None
        opt = {'cap': v['cap'] or None, 'ui_name': v['ui_name'] or None, 'title': v['title'] or None,
               'customs': self.customs.get(), 'fanfare': self.fanfare.get(),
               'weapons': [self.weapons.get(i) for i in self.weapons.curselection()]}
        if v['subtitle']:
            opt['subtitle'] = v['subtitle']
        for k in ('series', 'costumes', 'sort_key', 'kind', 'ui_id'):
            if v[k]:
                try:
                    opt[k] = int(v[k], 0)
                except ValueError:
                    pass
        if v['after'] and 'sort_key' not in opt:
            opt['after'] = int(v['after']) if v['after'].isdigit() else v['after']
        return self.session.fighter_spec(v['source'], v['name'], **opt)

    def stage_spec(self):
        v = {k: x.get().strip() for k, x in self.sv.items()}
        if not (v['source'] and v['name']):
            return None
        opt = {'title': v['title'] or None, 'page': int(v['page'] or 1)}
        if v['series']:
            opt['series'] = v['series']
        if v['cosmetic']:
            try:
                opt['cosmetic'] = int(v['cosmetic'], 0)
            except ValueError:
                pass
        return self.session.stage_spec(v['source'], v['name'], **opt)

    def _all(self):
        fs = list(self.pending_f)
        ss = list(self.pending_s)
        if self.session:
            f = self.fighter_spec()
            if f and not any(x['name'] == f['name'] for x in fs):
                fs.append(f)
            s = self.stage_spec()
            if s and not any(x['name'] == s['name'] for x in ss):
                ss.append(s)
        return fs, ss

    def _add_fighter(self):
        f = self.fighter_spec()
        if f:
            self.pending_f.append(f)
            self.plan_list.insert('end', 'fighter %s (from %s) kind 0x%X id %d' % (f['name'], f['source'], f['kind'],
                                                                                f['ui_id']))
            for k in ('name', 'cap', 'ui_name', 'title', 'subtitle'):
                self.fv[k].set('')

    def _add_stage(self):
        s = self.stage_spec()
        if s:
            self.pending_s.append(s)
            self.plan_list.insert('end', 'stage %s (from %s) cosmetic 0x%X' % (s['name'], s['source'], s['cosmetic']))
            self.sv['name'].set('')

    def _remove_pending(self):
        sel = self.plan_list.curselection()
        if not sel:
            return
        i = sel[0]
        text = self.plan_list.get(i)
        self.plan_list.delete(i)
        name = text.split()[1]
        self.pending_f = [f for f in self.pending_f if f['name'] != name]
        self.pending_s = [s for s in self.pending_s if s['name'] != name]

    # ------------------------------------------------------------ previews
    def _schedule_preview(self):
        if getattr(self, '_pv', None):
            self.root.after_cancel(self._pv)
        self._pv = self.root.after(400, self.preview)

    def preview(self):
        if not self.session:
            return
        fs, ss = self._all()
        try:
            reg = self.session.plan(fs, ss)[0]
        except Exception as e:
            self.css_info.configure(text='preview: %s' % e)
            return
        new_f = [f['ui_id'] for f in reg['fighters'] if f['name'] in {x['name'] for x in fs}]
        new_s = [s['cosmetic'] for s in reg['stages'] if s['name'] in {x['name'] for x in ss}]
        try:
            img, info = self.session.css(reg, new_f)
            self.css_img = photo(img, (640, 360))
            self.css_label.configure(image=self.css_img)
            slots = ', '.join('%s: slot %d of %d' % (f['ui_name'], info['slot'].get(f['ui_id'], 0), info['count'])
                              for f in reg['fighters'] if f['ui_id'] in new_f)
            self.css_info.configure(text='%s. %s%s' % (slots or 'no clone planned', info['note'],
                                                       ('; PROBLEM: ' + '; '.join(info['problems'])) if info['problems'] else ''))
            self.css_slots = info
        except Exception as e:
            self.css_info.configure(text='CSS preview: %s' % e)
        try:
            img, _info = self.session.sss(reg, new_s)
            self.sss_img = photo(img, (640, 360))
            self.sss_label.configure(image=self.sss_img)
        except Exception as e:
            self.say('SSS preview: %s' % e)

    # ------------------------------------------------------------ actions
    def check(self):
        if not self.session:
            return self.reload()
        fs, ss = self._all()
        reg, recs, errors, notes, files, items = self.session.plan(fs, ss)
        self.say('=== Check: %d fighter / %d stage clone(s)' % (len(fs), len(ss)))
        for n in notes:
            self.say('note: ' + n)
        for e in errors:
            self.say('ERROR: ' + e)
        self.say('files:')
        for f in files:
            self.say('  ' + f)
        self.say('executable:')
        for i in items:
            self.say('  ' + i)
        self.say('OK: ready to build' if not errors else '%d problem(s): fix them before Build' % len(errors))
        return not errors

    def build(self):
        if not self.session or not self.check():
            return
        fs, ss = self._all()
        portraits = {f['name']: self.portraits.get(f['name'], {}) for f in fs}
        icons = {s['name']: self.icons.get(s['name'], {}) for s in ss}

        def run():
            try:
                self.session.build(fs, ss, portraits, icons)
                self.say('=== Built into %s' % self.session.out)
                self.pending_f, self.pending_s = [], []
                self.root.after(0, lambda: (self.plan_list.delete(0, 'end'), self.reload()))
            except Exception as e:
                self.say('BUILD FAILED: %s' % e)
                self.say(traceback.format_exc())
        threading.Thread(target=run, daemon=True).start()

    def open_output(self):
        p = self.vars['out'].get()
        if not p:
            return
        os.makedirs(p, exist_ok=True)
        if sys.platform.startswith('win'):
            os.startfile(p)  # noqa
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', p])
        else:
            subprocess.Popen(['xdg-open', p])


def main():
    ap = argparse.ArgumentParser()
    for k in ('data', 'ui', 'exe', 'out'):
        ap.add_argument('--' + k)
    ap.add_argument('--screenshot')
    ap.add_argument('--tab', default='fighters')
    ap.add_argument('--fighter', help='with --screenshot: SOURCE:NAME to fill in')
    ap.add_argument('--stage', help='with --screenshot: SOURCE:NAME to fill in')
    a = ap.parse_args()
    root = tk.Tk()
    app = App(root, a)
    if a.screenshot:
        def shoot():
            app.reload()
            if a.fighter:
                src, name = a.fighter.split(':')
                f = next(x for x in R.base_choices(app.session.param_dirs(), app.session.reg) if x['name'] == src)
                app._pick_fighter(f)
                app.fv['name'].set(name)
            if a.stage:
                src, name, *pg = a.stage.split(':')
                app.sv['source'].set(src)
                app.sv['name'].set(name)
                app.sv['page'].set(pg[0] if pg else '1')
                app.sv['cosmetic'].set('0x%X' % (0x38 + len(app.session.reg['stages'])))
            if a.tab == 'stages':
                app.nb.select(1)
            app.preview()
            app.check()
            root.after(1500, grab)

        def grab():
            root.update()
            from PIL import ImageGrab
            x, y = root.winfo_rootx(), root.winfo_rooty()
            w, h = root.winfo_width(), root.winfo_height()
            ImageGrab.grab(bbox=(x, y, x + w, y + h), xdisplay=os.environ.get('DISPLAY')).save(a.screenshot)
            info = {'title': root.title(), 'fighters': app.f_count, 'fighter_icons': app.f_icon_count,
                    'css': {k: v for k, v in getattr(app, 'css_slots', {}).items() if k != 'slot'}}
            print(json.dumps(info))
            root.destroy()
        root.after(500, shoot)
    root.mainloop()


if __name__ == '__main__':
    main()
