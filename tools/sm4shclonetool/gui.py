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
        root.geometry('1480x1010')
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
        self.ftab, self.stab, self.xtab, self.vtab = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        nb.add(self.ftab, text='Fighters')
        nb.add(self.xtab, text='Fighter extras (call, fanfare, Kirby, plates, languages)')
        nb.add(self.vtab, text='Voices (a built clone)')
        nb.add(self.stab, text='Stages')
        self._fighter_tab()
        self._extras_tab()
        self._voices_tab()
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
                  ('subtitle', 'Title line (CSS, Boxing Ring)'), ('series', 'Series icon id'), ('costumes', 'Costumes'),
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
        self.independent = tk.BooleanVar(value=True)
        self.own_sound = tk.BooleanVar(value=True)
        self.own_effects = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='Fully independent clone (recommended): own sounds, effects and articles',
                        variable=self.independent, command=self._preset).pack(anchor='w')
        ttk.Checkbutton(opt, text='  Own sound bank (copy of the base\'s)', variable=self.own_sound).pack(anchor='w')
        ttk.Checkbutton(opt, text='  Own effect bank (copy of the base\'s)', variable=self.own_effects).pack(anchor='w')
        self.random = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='In the random select', variable=self.random).pack(anchor='w')
        self.customs = tk.BooleanVar(value=True)
        self.fanfare = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='Custom moves (owns the base\'s; menu labels / icons)', variable=self.customs).pack(anchor='w')
        ttk.Checkbutton(opt, text='Victory fanfare and KO voices (sound config records)', variable=self.fanfare).pack(anchor='w')
        af = ttk.Frame(opt)
        af.pack(fill='x')
        ttk.Label(af, text='Own articles (selected; without an own sound bank they keep the base\'s sounds):').pack(side='left')
        ttk.Button(af, text='All', width=4, command=lambda: self.weapons.select_set(0, 'end')).pack(side='right')
        self.weapons = tk.Listbox(opt, selectmode='multiple', height=3, exportselection=False)
        self.weapons.pack(fill='x')
        ttk.Label(opt, text='Announcer call, fanfare, Kirby\'s copy, name plates, languages: the "Fighter extras" tab.',
                  foreground='#205080').pack(anchor='w')
        pf = ttk.LabelFrame(mid, text='Portraits (default: the base\'s, new texture ids)')
        pf.pack(fill='x', pady=4)
        self.p_set = ttk.Combobox(pf, values=PORTRAIT_SETS, width=9, state='readonly')
        self.p_set.set('chr_00')
        self.p_set.grid(row=0, column=0)
        self.p_nn = ttk.Combobox(pf, values=['all'] + ['%02d' % i for i in range(1, 17)] + [''], width=4)
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

    def _extras_tab(self):
        t = self.xtab
        left = ttk.Frame(t)
        left.pack(side='left', fill='y', padx=6, pady=4)
        self.x = {}

        def radio(parent, key, values, default):
            v = tk.StringVar(value=default)
            self.x[key] = v
            fr = ttk.Frame(parent)
            fr.pack(anchor='w')
            for val, label in values:
                ttk.Radiobutton(fr, text=label, value=val, variable=v,
                                command=self._schedule_plate).pack(side='left')
            return fr

        def wav_row(parent, key):
            v = tk.StringVar()
            self.x[key] = v
            fr = ttk.Frame(parent)
            fr.pack(fill='x')
            ttk.Entry(fr, textvariable=v, width=40).pack(side='left')
            ttk.Button(fr, text='WAV...', command=lambda: v.set(filedialog.askopenfilename(
                filetypes=[('WAV', '*.wav'), ('all', '*.*')]) or v.get())).pack(side='left')
            ttk.Button(fr, text='Preview', command=lambda k=key: self._preview_sound(k)).pack(side='left')
        a = ttk.LabelFrame(left, text='Announcer call (character select and results screen)')
        a.pack(fill='x', pady=3)
        radio(a, 'call', [('own', 'Own copy of the base\'s (default)'), ('share', 'Share the base\'s'),
                          ('wav', 'Import WAV')], 'own')
        wav_row(a, 'call_wav')
        m = ttk.LabelFrame(left, text='Victory fanfare (results screen; the results music after it is the mode\'s)')
        m.pack(fill='x', pady=3)
        radio(m, 'music', [('own', 'Own copy of the base\'s (default)'), ('share', 'Share the base\'s'),
                           ('wav', 'Import WAV')], 'own')
        wav_row(m, 'music_wav')
        k = ttk.LabelFrame(left, text='Kirby\'s copy of the clone')
        k.pack(fill='x', pady=3)
        self.x_kirby = tk.BooleanVar(value=True)
        ttk.Checkbutton(k, text='Kirby copies the clone (its base\'s copy ability)', variable=self.x_kirby).pack(anchor='w')
        radio(k, 'kirby_hat', [('own', 'Own hat + copy motions (copies of the base\'s)'), ('share', 'The base\'s')], 'own')
        hf = ttk.Frame(k)
        hf.pack(fill='x')
        self.x['kirby_hat_dir'] = tk.StringVar()
        ttk.Label(hf, text='Import hat model folder:').pack(side='left')
        ttk.Entry(hf, textvariable=self.x['kirby_hat_dir'], width=28).pack(side='left')
        ttk.Button(hf, text='Folder...', command=lambda: self.x['kirby_hat_dir'].set(
            filedialog.askdirectory() or self.x['kirby_hat_dir'].get())).pack(side='left')
        ttk.Button(hf, text='Show hat', command=self._show_hat).pack(side='left')
        self.x_hat_info = ttk.Label(k, text='', wraplength=520)
        self.x_hat_info.pack(anchor='w')
        lg = ttk.LabelFrame(left, text='Names in every language (empty: the title / title line above)')
        lg.pack(fill='x', pady=3)
        self.lang_tree = ttk.Treeview(lg, columns=('title', 'subtitle'), height=5)
        self.lang_tree.heading('#0', text='language')
        self.lang_tree.heading('title', text='title')
        self.lang_tree.heading('subtitle', text='title line (Boxing Ring)')
        self.lang_tree.column('#0', width=90)
        self.lang_tree.pack(fill='x')
        ef = ttk.Frame(lg)
        ef.pack(fill='x')
        self.x['lang_title'] = tk.StringVar()
        self.x['lang_sub'] = tk.StringVar()
        ttk.Entry(ef, textvariable=self.x['lang_title'], width=22).pack(side='left')
        ttk.Entry(ef, textvariable=self.x['lang_sub'], width=22).pack(side='left')
        ttk.Button(ef, text='Set for the selected language', command=self._set_lang).pack(side='left')
        self.lang_over = {}
        right = ttk.LabelFrame(t, text='Name plates (chrn_*): the game\'s style; preview of the plate')
        right.pack(side='left', fill='both', expand=True, padx=6, pady=4)
        pf = ttk.Frame(right)
        pf.pack(fill='x')
        ttk.Label(pf, text='Plate text (empty: the title; a line break: \\n):').grid(row=0, column=0, sticky='w')
        self.x['plate'] = tk.StringVar()
        ttk.Entry(pf, textvariable=self.x['plate'], width=30).grid(row=0, column=1)
        ttk.Label(pf, text='Lines:').grid(row=0, column=2)
        self.x['plate_lines'] = tk.StringVar(value='auto')
        ttk.Combobox(pf, textvariable=self.x['plate_lines'], values=['auto', '1', '2'], width=5,
                     state='readonly').grid(row=0, column=3)
        self.font_vars = {}
        for i, (tt, label) in enumerate((('plate', 'Font: name plates'), ('title', 'Font: titles'),
                                         ('other', 'Font: other text images'))):
            ttk.Label(pf, text=label).grid(row=1 + i, column=0, sticky='w')
            v = tk.StringVar(value='bundled')
            self.font_vars[tt] = v
            ttk.Combobox(pf, textvariable=v, values=['bundled', 'mincho', 'gothic', 'game'], width=28).grid(
                row=1 + i, column=1, sticky='w')
            ttk.Button(pf, text='Choose font file...', command=lambda v=v: v.set(filedialog.askopenfilename(
                filetypes=[('fonts', '*.ttf *.otf *.ttc'), ('all', '*.*')]) or v.get())).grid(row=1 + i, column=2,
                                                                                          columnspan=2)
            v.trace_add('write', lambda *_: self._schedule_plate())
        self.x['plate'].trace_add('write', lambda *_: self._schedule_plate())
        self.x['plate_lines'].trace_add('write', lambda *_: self._schedule_plate())
        self.plate_label = tk.Label(right, background='#404040')
        self.plate_label.pack(fill='both', expand=True)
        self.plate_info = ttk.Label(right, text='')
        self.plate_info.pack(fill='x')

    def _schedule_plate(self):
        if getattr(self, '_pp', None):
            self.root.after_cancel(self._pp)
        self._pp = self.root.after(300, self.plate_preview)

    def _font_choice(self, tt):
        v = self.font_vars[tt].get().strip()
        return None if v in ('', 'bundled') else v

    def plate_preview(self):
        from sm4shclonetool import plates as PL
        try:
            text = self.x['plate'].get().replace('\\n', '\n') or self.fv['title'].get() or self.fv['name'].get() \
                or 'Clone'
            lines = None if self.x['plate_lines'].get() == 'auto' else int(self.x['plate_lines'].get())
            dirs = [self.vars['data'].get()] if self.vars['data'].get() else []
            font = PL.resolve_font(self._font_choice('plate'), 'plate', dirs)
            from PIL import Image
            pics = []
            for st in ('chrn_40', 'chrn_11', 'chrn_12'):
                style = None
                base = self.fv['source'].get()
                if self.session and base:
                    ui = next((f['ui_name'] for f in R.base_choices(self.session.param_dirs(), self.session.reg)
                               if f['name'] == base), None)
                    q = T.find_icon(self.session.ui_dirs(), [st], ui) if ui else None
                    img = T.decode(q) if q else None
                    style = PL.plate_style(img) if img is not None else None
                pics.append(PL.render(text, st, font, None, style, lines)[0])
            w = max(p.size[0] for p in pics)
            out = Image.new('RGBA', (w, sum(p.size[1] + 6 for p in pics)), (64, 64, 64, 255))
            y = 0
            for p in pics:
                out.paste(p, (0, y), p)
                y += p.size[1] + 6
            self.plate_img = photo(out, (760, 600))
            self.plate_label.configure(image=self.plate_img)
            self.plate_info.configure(text='%s; font %s' % (' / '.join(PL.split_lines(text, lines)),
                                                            os.path.basename(font or '?')))
        except Exception as e:
            self.plate_info.configure(text='plate preview: %s' % e)

    def _preview_sound(self, key):
        from sm4shclonetool import audio as AU
        p = self.x[key].get()
        if p and os.path.exists(p):
            AU.play(p)
            return
        if key == 'call_wav' and self.session:
            from sm4shclonetool import narration as N
            base = self.fv['source'].get()
            rec = next((f for f in R.base_choices(self.session.param_dirs(), self.session.reg) if f['name'] == base),
                       None)
            if rec:
                tones = N.call_tones({'ui_id': rec['id'], 'base_ui_id': rec['id']}, self.session.data,
                                     self.session.pkg_data)
                if tones:
                    AU.play(tones[0][1])
                    return
        self.say('no sound to preview (choose a WAV, or the data folder has no narration bank for the base)')

    def _show_hat(self):
        d = self.x['kirby_hat_dir'].get()
        if d and os.path.isdir(d):
            fs = [os.path.relpath(os.path.join(r, f), d) for r, _ds, fl in os.walk(d) for f in fl]
            self.x_hat_info.configure(text='hat folder: %d files: %s' % (len(fs), ', '.join(fs[:8])))
            return
        base = self.fv['source'].get()
        if not (self.session and base and self.session.exe):
            self.x_hat_info.configure(text='pick a base fighter (and the executable) first')
            return
        from sm4shclonetool.rpx import Rpx
        from sm4shclonetool import fighter as F
        x = Rpx(self.session.exe)
        try:
            bk = R.KINDS.index(next(f['base'] for f in self.session.reg['fighters'] if f['name'] == base)
                               if any(f['name'] == base for f in self.session.reg['fighters']) else base)
        except ValueError:
            return
        hat = F._rstr(x.r32, x.r32(F.KIRBY_HAT + 4 * bk))
        body = F._rstr(x.r32, x.r32(F.KIRBY_BODY + 4 * bk))
        d = os.path.join(self.session.data, 'fighter', 'kirby')
        self.x_hat_info.configure(text='the base\'s copy: hat fighter/kirby/model/%s/ (%s), motions motion/%sbody/ (%s)'
                                  % (hat, 'in your data' if hat and os.path.isdir(os.path.join(d, 'model', hat))
                                     else 'not in your data', body,
                                     'in your data' if body and os.path.isdir(os.path.join(d, 'motion', body + 'body'))
                                     else 'not in your data'))

    def _fill_languages(self):
        from sm4shclonetool import languages as L
        self.lang_tree.delete(*self.lang_tree.get_children())
        if not self.session:
            return
        for key, _p in L.languages(self.session.data):
            o = self.lang_over.get(key, {})
            self.lang_tree.insert('', 'end', iid=key, text=key, values=(o.get('title', ''), o.get('subtitle', '')))

    def _set_lang(self):
        sel = self.lang_tree.selection()
        for key in sel:
            o = {}
            if self.x['lang_title'].get().strip():
                o['title'] = self.x['lang_title'].get().strip()
            if self.x['lang_sub'].get().strip():
                o['subtitle'] = self.x['lang_sub'].get().strip()
            self.lang_over[key] = o
        self._fill_languages()

    def extras_opts(self):
        o = {'call': self.x['call'].get(), 'music': self.x['music'].get(), 'kirby': self.x_kirby.get(),
             'kirby_hat_mode': self.x['kirby_hat'].get()}
        for k in ('call', 'music'):
            if o[k] == 'wav':
                if self.x[k + '_wav'].get():
                    o[k + '_wav'] = self.x[k + '_wav'].get()
                else:
                    o[k] = 'own'
        if self.x['kirby_hat_dir'].get():
            o['kirby_hat_dir'] = self.x['kirby_hat_dir'].get()
        if self.x['plate'].get():
            o['plate_text'] = self.x['plate'].get().replace('\\n', '\n')
        if self.x['plate_lines'].get() != 'auto':
            o['plate_lines'] = int(self.x['plate_lines'].get())
        fonts = {tt: self._font_choice(tt) for tt in self.font_vars if self._font_choice(tt)}
        if fonts:
            o['fonts'] = fonts
        titles = {k: v for k, v in self.lang_over.items() if v and k != 'main'}
        if titles:
            o['titles'] = titles
        return o

    def _voices_tab(self):
        t = self.vtab
        top = ttk.Frame(t)
        top.pack(fill='x', padx=6, pady=4)
        ttk.Label(top, text='Clone (built in this project):').pack(side='left')
        self.v_clone = ttk.Combobox(top, width=20, state='readonly')
        self.v_clone.pack(side='left')
        self.v_clone.bind('<<ComboboxSelected>>', lambda e: self._fill_voices())
        ttk.Button(top, text='Refresh', command=self._fill_voices).pack(side='left', padx=4)
        ttk.Button(top, text='Preview', command=self._voice_play).pack(side='left')
        ttk.Button(top, text='Replace with WAV...', command=self._voice_replace).pack(side='left', padx=4)
        ttk.Button(top, text='Import a folder of WAVs (by tone name)...', command=self._voice_folder).pack(side='left')
        ttk.Label(t, text='Every line of the clone\'s own banks (voice, sounds, cheer, Kirby\'s copy voices). A line the '
                  'game plays from code by the base\'s id (KO screams, damage, MSC) plays this same tone: the clone\'s '
                  'banks answer for the base\'s ids. Replacing changes only the clone\'s package files.',
                  wraplength=1300).pack(fill='x', padx=6)
        self.v_tree = ttk.Treeview(t, columns=('name', 'bank', 'secs'), height=28)
        for c, w, h in (('#0', 110, 'category'), ('name', 420, 'tone'), ('bank', 360, 'bank:tone'), ('secs', 70, 's')):
            self.v_tree.heading(c, text=h)
            self.v_tree.column(c, width=w)
        self.v_tree.pack(fill='both', expand=True, padx=6, pady=4)
        self.v_lines = []

    def _voice_rec(self):
        name = self.v_clone.get()
        return next((f for f in (self.session.reg['fighters'] if self.session else []) if f['name'] == name), None)

    def _fill_voices(self):
        from sm4shclonetool import voices as V
        if self.session:
            self.v_clone.configure(values=[f['name'] for f in self.session.reg['fighters']])
        rec = self._voice_rec()
        self.v_tree.delete(*self.v_tree.get_children())
        if not rec:
            return
        self.v_lines = sorted(V.lines(rec, self.session.pkg_data), key=lambda x: (x['category'], x['name']))
        for i, x in enumerate(self.v_lines):
            self.v_tree.insert('', 'end', iid=str(i), text=x['category'],
                               values=(x['name'], '%s:%d' % (x['file'], x['tone']), '%.2f' % x['seconds']))

    def _voice_sel(self):
        sel = self.v_tree.selection()
        return [self.v_lines[int(i)] for i in sel] if sel else []

    def _voice_play(self):
        from sm4shclonetool import audio as AU
        from sm4shclonetool import voices as V
        for x in self._voice_sel()[:1]:
            AU.play(V.tone_data(self._voice_rec(), self.session.pkg_data, x['file'], x['tone']))

    def _voice_replace(self):
        from sm4shclonetool import voices as V
        sel = self._voice_sel()
        if not sel:
            return
        p = filedialog.askopenfilename(filetypes=[('WAV', '*.wav'), ('all', '*.*')])
        if p:
            for x in sel:
                V.replace(self._voice_rec(), self.session.pkg_data, x['file'], x['tone'], p)
                self.say('voice %s replaced with %s' % (x['name'], os.path.basename(p)))
            self._fill_voices()

    def _voice_folder(self):
        from sm4shclonetool import voices as V
        rec = self._voice_rec()
        d = filedialog.askdirectory()
        if rec and d:
            for w, f, n in V.import_folder(rec, self.session.pkg_data, d):
                self.say('voice %s (%s) <- %s' % (n, f, w))
            self._fill_voices()

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
        self.s_random = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text='In the random stage select', variable=self.s_random).grid(row=6, column=0,
                                                                                         columnspan=2, sticky='w')
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
        self.limits_label = ttk.Label(self.root, text='', foreground='#205080')
        self.limits_label.pack(fill='x', padx=8)
        f = ttk.Frame(self.root)
        f.pack(fill='both', padx=6, pady=4)
        left = ttk.Frame(f)
        left.pack(side='left', fill='y')
        ttk.Label(left, text='Plan (built together):').pack(anchor='w')
        self.plan_list = tk.Listbox(left, height=4, width=48)
        self.plan_list.pack()
        btn = ttk.Frame(left)
        btn.pack(fill='x', pady=4)
        ttk.Button(btn, text='Check', command=self.check).pack(side='left')
        ttk.Button(btn, text='Build', command=self.build).pack(side='left', padx=4)
        ttk.Button(btn, text='Open output', command=self.open_output).pack(side='left')
        self.log = tk.Text(f, height=8, wrap='word', background='#10141c', foreground='#d8e0f0')
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
        self._fill_languages()
        self._fill_voices()
        self._schedule_preview()
        self._schedule_plate()

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
        for a in s.articles(f['name']):
            self.weapons.insert('end', a)
        if self.independent.get():
            self.weapons.select_set(0, 'end')

    def _preset(self):
        on = self.independent.get()
        self.own_sound.set(on)
        self.own_effects.set(on)
        if on:
            self.weapons.select_set(0, 'end')
        else:
            self.weapons.select_clear(0, 'end')

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
            nn = self.p_nn.get()
            try:
                n = int(self.fv['costumes'].get() or 8)
            except ValueError:
                n = 8
            for k in (['%02d' % i for i in range(1, n + 1)] if nn == 'all' else [nn]):   # one PNG for every costume
                self.portraits.setdefault(name, {})[(self.p_set.get(), k)] = p
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
               'customs': self.customs.get(), 'fanfare': self.fanfare.get(), 'random': self.random.get(),
               'own_sound': self.own_sound.get(), 'own_effects': self.own_effects.get(),
               'weapons': [self.weapons.get(i) for i in self.weapons.curselection()]}
        opt.update(self.extras_opts())
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
        opt = {'title': v['title'] or None, 'page': int(v['page'] or 1), 'random': self.s_random.get()}
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
            self.limits_label.configure(text=self.session.limits_text(reg))
        except Exception as e:
            self.limits_label.configure(text='limits: %s' % e)
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
    ap.add_argument('--tab', default='fighters', help='fighters, extras, voices or stages')
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
            tabs = {'fighters': 0, 'extras': 1, 'voices': 2, 'stages': 3}
            app.nb.select(tabs.get(a.tab, 0))
            if a.tab == 'voices' and app.session:
                for f in reversed(app.session.reg['fighters']):      # the last clone that has sound banks
                    app.v_clone.set(f['name'])
                    app._fill_voices()
                    if app.v_lines:
                        break
            app.preview()
            app.plate_preview()
            app.check()
            root.after(1500, grab)

        def grab():
            root.update()
            from PIL import ImageGrab
            x, y = root.winfo_rootx(), root.winfo_rooty()
            w, h = root.winfo_width(), root.winfo_height()
            ImageGrab.grab(bbox=(x, y, x + w, y + h), xdisplay=os.environ.get('DISPLAY')).save(a.screenshot)
            info = {'title': root.title(), 'fighters': app.f_count, 'fighter_icons': app.f_icon_count,
                    'css': {k: v for k, v in getattr(app, 'css_slots', {}).items() if k != 'slot'},
                    'limits': app.limits_label.cget('text'), 'plate': app.plate_info.cget('text'),
                    'voices': len(app.v_lines), 'languages': len(app.lang_tree.get_children())}
            print(json.dumps(info))
            root.destroy()
        root.after(500, shoot)
    root.mainloop()


if __name__ == '__main__':
    main()
