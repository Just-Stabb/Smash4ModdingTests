using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Media;
using System.Windows.Forms;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Sound;

namespace Sm4shCommand.GUI
{
    /// <summary>
    /// Tools > Sound Effect Viewer (v1.7.32, Ctrl+Shift+E): the open fighter's sounds (fighter/NAME/sound: se, its costume
    /// banks, vc, cheer, Kirby copy) and the common ones (sound/se/snd_se_joucyu, row 0), each with the sound id ACMD
    /// plays it by (soundlabeltable.bin: row &lt;&lt; 16 | label), its tone, bank, length, loop and volume, and your alias
    /// (Aliases/sounds/FIGHTER.txt, common.txt). Play decodes the tone (DSP-ADPCM) and plays it at the bank's volume;
    /// Add to Script puts the chosen sound command with the id below the caret in the open script.
    /// v1.7.33, the Sound Adder: Add sounds.. (SoundAdderDialog) adds audio files to one of the fighter's banks as new
    /// tones with ids no other sound has; they are listed as new / unsaved rows (preview, alias, filter, Add to Script as
    /// any other) and the Volume column of the fighter's list can be edited (the TONE volume, dB); Save writes the banks
    /// and soundlabeltable.bin in place (backups first), Save to.. under a folder laid out as the game's data, ready to
    /// install (Sound.SoundAdder).
    /// </summary>
    public class SoundViewer : Form
    {
        FighterSounds sounds;
        readonly Func<ITS_EDITOR> activeEditor;

        readonly Label fighterLabel = new Label { AutoSize = true, Padding = new Padding(0, 6, 8, 0), Font = new Font(SystemFonts.MessageBoxFont, FontStyle.Bold) };
        readonly Button pickFighter = new Button { Text = "Fighter..", AutoSize = true };
        readonly Button pickData = new Button { Text = "Game data..", AutoSize = true };
        readonly Button reload = new Button { Text = "Reload", AutoSize = true };
        readonly TextBox filter = new TextBox { Width = 180 };
        readonly ComboBox bankFilter = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 120 };
        readonly TabControl tabs = new TabControl { Dock = DockStyle.Fill };
        readonly TabPage fighterTab = new TabPage("Fighter sounds"), commonTab = new TabPage("Common sounds"), banksTab = new TabPage("Banks");
        readonly DataGridView fighterGrid = Grid(true), commonGrid = Grid(false);
        readonly Button addSounds = new Button { Text = "Add sounds..", AutoSize = true };
        readonly Button save = new Button { Text = "Save", AutoSize = true, Enabled = false };
        readonly Button saveTo = new Button { Text = "Save to..", AutoSize = true, Enabled = false };
        readonly Button discard = new Button { Text = "Discard", AutoSize = true, Enabled = false };
        SoundAdder adder;
        readonly ComboBox commonBank = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 260 };
        readonly Label commonNote = new Label { AutoSize = true, Padding = new Padding(6, 6, 0, 0), ForeColor = Color.DimGray };
        readonly TextBox banksText = new TextBox { Multiline = true, ReadOnly = true, Dock = DockStyle.Fill, ScrollBars = ScrollBars.Both, WordWrap = false, Font = new Font(FontFamily.GenericMonospace, 8.5f) };
        readonly Button play = new Button { Text = "Play", Width = 64 };
        readonly Button stop = new Button { Text = "Stop", Width = 64 };
        readonly CheckBox loop = new CheckBox { Text = "Loop (looping tones)", AutoSize = true, Checked = true };
        readonly CheckBox bankVolume = new CheckBox { Text = "Bank volume", AutoSize = true, Checked = true };
        readonly NumericUpDown gain = new NumericUpDown { Minimum = -40, Maximum = 20, Value = 0, DecimalPlaces = 1, Increment = 1, Width = 60 };
        readonly ComboBox command = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 300 };
        readonly Button addToScript = new Button { Text = "Add to Script", AutoSize = true };
        readonly Button copyId = new Button { Text = "Copy ID", AutoSize = true };
        readonly Button copyLine = new Button { Text = "Copy Line", AutoSize = true };
        readonly Label info = new Label { Dock = DockStyle.Fill, AutoEllipsis = true, Padding = new Padding(4, 2, 4, 2) };
        readonly Label status = new Label { Dock = DockStyle.Bottom, Height = 18, ForeColor = Color.DimGray, AutoEllipsis = true };
        readonly ToolTip tips = new ToolTip();
        SoundPlayer player;
        MemoryStream playing;
        bool filling;

        /// <summary>The sound commands Add to Script offers: (command, what it does). The game's own scripts use each
        /// (vanilla Dr. Mario's and Kirby's sound.bin: Sound_Effect 222 times with common ids, row 0, besides their own).</summary>
        public static readonly string[][] Commands =
        {
            new[] { "Sound_Effect", "PLAY_SE: plays it once (common or own)" },
            new[] { "Transient_Sound_Effect", "PLAY_STATUS: plays it until the status ends (loops)" },
            new[] { "Stop_Sound_Effect", "STOP_SE: stops it" },
            new[] { "PLAY_SE_REMAIN", "plays it, kept past the status' end" },
            new[] { "PLAY_SE_NO_3D", "plays it without 3D placement" },
            new[] { "Sound_Effect3", "PLAY_LANDING_SE: a landing sound" },
            new[] { "Sound_Effect4", "PLAY_DOWN_SE: a falling-down sound" },
            new[] { "Sound_Effect2", "PLAY_STEP: a step sound" },
        };

        static DataGridView Grid(bool volumeEditable)
        {
            var g = new DataGridView
            {
                Dock = DockStyle.Fill, AllowUserToAddRows = false, AllowUserToDeleteRows = false, RowHeadersVisible = false,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect, MultiSelect = false, AllowUserToResizeRows = false,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.None, EditMode = DataGridViewEditMode.EditOnKeystrokeOrF2,
            };
            Action<string, string, int, bool> col = (name, head, w, edit) =>
            {
                var c = new DataGridViewTextBoxColumn { Name = name, HeaderText = head, Width = w, ReadOnly = !edit, SortMode = DataGridViewColumnSortMode.Automatic };
                if (edit) c.DefaultCellStyle.BackColor = Color.FromArgb(255, 255, 230);
                g.Columns.Add(c);
            };
            col("Id", "Sound ID", 86, false);
            col("Name", "Tone (label)", 250, false);
            col("Alias", "Alias (yours)", 170, true);
            col("Bank", "Bank", 80, false);
            col("Length", "Length (s)", 66, false);
            col("Loop", "Loop", 44, false);
            col("Ch", "Ch", 30, false);
            col("Rate", "Rate", 50, false);
            col("Volume", "Volume (dB)", 72, volumeEditable);      // v1.7.33: the fighter's tones' level, saved with Save
            col("Tone", "Tone #", 50, false);
            col("Note", "Note", 220, false);
            g.Columns["Id"].DefaultCellStyle.Font = new Font(FontFamily.GenericMonospace, 8.5f);
            return g;
        }

        public SoundViewer(string fighterRoot, Func<ITS_EDITOR> activeEditor)
        {
            this.activeEditor = activeEditor;
            Text = "Sound Effect Viewer";
            Size = new Size(1180, 680);
            StartPosition = FormStartPosition.CenterParent;
            Build();
            LoadFighter(fighterRoot);
        }

        /// <summary>The loaded sounds (tests read them).</summary>
        public FighterSounds Sounds { get { return sounds; } }
        public DataGridView FighterGrid { get { return fighterGrid; } }
        public DataGridView CommonGrid { get { return commonGrid; } }
        public TabControl Tabs { get { return tabs; } }
        public ComboBox CommandBox { get { return command; } }
        public TextBox Filter { get { return filter; } }
        /// <summary>v1.7.33: the pending additions / volume changes (the tests).</summary>
        public SoundAdder Adder { get { return adder; } }
        /// <summary>v1.7.33: the Add sounds.. dialog the tests fill instead of showing it modally (null: shown).</summary>
        public Action<SoundAdderDialog> AdderDialogHook;
        /// <summary>v1.7.33: Save's confirmation (the tests answer it; null asks).</summary>
        public Func<string, bool> ConfirmSave;

        void Build()
        {
            var top = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 32, WrapContents = false, Padding = new Padding(4, 3, 4, 0) };
            top.Controls.Add(fighterLabel);
            top.Controls.Add(pickFighter);
            top.Controls.Add(pickData);
            top.Controls.Add(reload);
            top.Controls.Add(new Label { Text = "Filter (name, alias, ID):", AutoSize = true, Padding = new Padding(12, 6, 0, 0) });
            top.Controls.Add(filter);
            top.Controls.Add(new Label { Text = "Bank:", AutoSize = true, Padding = new Padding(8, 6, 0, 0) });
            top.Controls.Add(bankFilter);
            top.Controls.Add(new Label { Text = "", AutoSize = true, Padding = new Padding(6, 0, 0, 0) });
            top.Controls.Add(addSounds);
            top.Controls.Add(save);
            top.Controls.Add(saveTo);
            top.Controls.Add(discard);

            fighterTab.Controls.Add(fighterGrid);
            var commonTop = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 30, WrapContents = false, Padding = new Padding(2, 2, 2, 0) };
            commonTop.Controls.Add(new Label { Text = "Bank:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) });
            commonTop.Controls.Add(commonBank);
            commonTop.Controls.Add(commonNote);
            commonTab.Controls.Add(commonGrid);
            commonTab.Controls.Add(commonTop);
            banksTab.Controls.Add(banksText);
            tabs.TabPages.Add(fighterTab);
            tabs.TabPages.Add(commonTab);
            tabs.TabPages.Add(banksTab);

            var bottom = new Panel { Dock = DockStyle.Bottom, Height = 92 };
            var row1 = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 32, WrapContents = false, Padding = new Padding(4, 3, 4, 0) };
            row1.Controls.Add(play);
            row1.Controls.Add(stop);
            row1.Controls.Add(loop);
            row1.Controls.Add(bankVolume);
            row1.Controls.Add(new Label { Text = "Gain (dB):", AutoSize = true, Padding = new Padding(6, 6, 0, 0) });
            row1.Controls.Add(gain);
            row1.Controls.Add(new Label { Text = "Command:", AutoSize = true, Padding = new Padding(16, 6, 0, 0) });
            row1.Controls.Add(command);
            row1.Controls.Add(addToScript);
            row1.Controls.Add(copyId);
            row1.Controls.Add(copyLine);
            bottom.Controls.Add(info);
            bottom.Controls.Add(row1);

            Controls.Add(tabs);
            Controls.Add(top);
            Controls.Add(bottom);
            Controls.Add(status);

            foreach (var c in Commands) command.Items.Add(c[0] + "  (" + c[1] + ")");
            command.SelectedIndex = 0;
            bankFilter.Items.Add("All banks");
            bankFilter.SelectedIndex = 0;

            tips.SetToolTip(filter, "Shows the sounds whose tone name, alias, bank or sound ID has this (both tabs, as you type; case doesn't matter).\n" +
                                    "IDs: hex with or without 0x, any part (0768, 5B, 0x768005B), or decimal. Empty: every sound.");
            tips.SetToolTip(pickFighter, "Open another fighter's folder (fighter\\NAME, with its sound folder).");
            tips.SetToolTip(pickData, "The game's data folder (a dump's content\\patch\\data ...) for sound\\config\\soundlabeltable.bin and the common bank\n" +
                                      "sound\\se\\snd_se_joucyu.nus3bank, when they aren't above the fighter's folder (a mod folder). Remembered.");
            tips.SetToolTip(loop, "A tone that loops in game (its loop points) plays its loop a few times, as it would until stopped.");
            tips.SetToolTip(bankVolume, "Play at the volume the bank gives the tone (its Volume column, dB), as the game does.");
            tips.SetToolTip(gain, "Extra preview gain (dB), for the preview only.");
            tips.SetToolTip(addToScript, "Adds the command with the sound's ID on a new line below the caret in the open script (its sound script, or any ACMD script).");
            tips.SetToolTip(copyId, "Copies the sound ID (0x...), as a sound command takes it.");
            tips.SetToolTip(copyLine, "Copies the command line (Command, with the sound's ID).");
            tips.SetToolTip(addSounds, "Add audio files (WAV; MP3 / OGG / FLAC ... through Windows or ffmpeg) to one of the fighter's banks as new sounds,\n" +
                                       "with ids no other sound has. They are listed as new / unsaved until Save.");
            tips.SetToolTip(save, "Writes the changed banks into the fighter's sound folder and soundlabeltable.bin (the mod's own, above the fighter's folder),\n" +
                                  "each replaced file backed up first (FILE.yyyyMMdd-HHmmss.bak).");
            tips.SetToolTip(saveTo, "Writes them under a folder of your choice laid out as the game's data, ready to install:\n" +
                                    "fighter\\NAME\\sound\\<bank>.nus3bank and sound\\config\\soundlabeltable.bin.");
            tips.SetToolTip(discard, "Drops the new sounds and volume changes not saved yet.");
            addSounds.Click += (o, e) => ShowAdder();
            save.Click += (o, e) => SaveChanges(null);
            saveTo.Click += (o, e) => SaveTo();
            discard.Click += (o, e) => { if (adder != null) { adder.Discard(); Fill(); UpdateChanges(); } };

            play.Click += (o, e) => Play();
            stop.Click += (o, e) => StopPlaying();
            reload.Click += (o, e) => { if (ConfirmDrop()) LoadFighter(sounds != null ? sounds.Root : null); };
            pickFighter.Click += (o, e) => PickFighter();
            pickData.Click += (o, e) => PickData();
            filter.TextChanged += (o, e) => Fill();
            bankFilter.SelectedIndexChanged += (o, e) => { if (!filling) Fill(); };
            commonBank.SelectedIndexChanged += (o, e) =>
            {
                if (filling || sounds == null || commonBank.SelectedIndex < 0) return;
                var path = ((BankItem)commonBank.SelectedItem).Path;
                sounds.LoadCommon(path);
                Fill();
            };
            addToScript.Click += (o, e) => AddToScript();
            copyId.Click += (o, e) => { var s = Selected; if (s != null && s.Id.HasValue) SetClipboard(s.IdText); };
            copyLine.Click += (o, e) => { var s = Selected; if (s != null && s.Id.HasValue) SetClipboard(CommandLine(SelectedCommand, s.Id.Value)); };
            tabs.SelectedIndexChanged += (o, e) => ShowInfo();
            foreach (var g in new[] { fighterGrid, commonGrid })
            {
                var grid = g;
                grid.SelectionChanged += (o, e) => ShowInfo();
                grid.CellDoubleClick += (o, e) => { if (e.RowIndex >= 0 && grid.Columns[e.ColumnIndex].ReadOnly) Play(); };
                grid.CellEndEdit += (o, e) => { AliasEdited(grid, e.RowIndex, e.ColumnIndex); VolumeEdited(grid, e.RowIndex, e.ColumnIndex); };
                grid.KeyDown += (o, e) => { if (e.KeyCode == Keys.Enter && !grid.IsCurrentCellInEditMode) { Play(); e.Handled = true; } };
                grid.SortCompare += (o, e) =>
                {
                    // numbers as numbers (length, volume, tone #, rate)
                    double a, b;
                    if (double.TryParse(Convert.ToString(e.CellValue1, CultureInfo.InvariantCulture), NumberStyles.Float, CultureInfo.InvariantCulture, out a) &&
                        double.TryParse(Convert.ToString(e.CellValue2, CultureInfo.InvariantCulture), NumberStyles.Float, CultureInfo.InvariantCulture, out b))
                    {
                        e.SortResult = a.CompareTo(b);
                        e.Handled = true;
                    }
                };
            }
            FormClosed += (o, e) => StopPlaying();
            FormClosing += (o, e) =>
            {
                if (e.CloseReason == CloseReason.UserClosing && adder != null && adder.HasChanges &&
                    MessageBox.Show(this, "The new sounds / volume changes aren't saved. Close and lose them?", "Sound Effect Viewer", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
                    e.Cancel = true;
            };
        }

        class BankItem
        {
            public string Path;
            public override string ToString() { return System.IO.Path.GetFileName(Path); }
        }

        static void SetClipboard(string text)
        {
            try { Clipboard.SetText(text); } catch (Exception) { }
        }

        /// <summary>Loads a fighter folder (fighter\NAME); null shows an empty viewer.</summary>
        public void LoadFighter(string root)
        {
            StopPlaying();
            adder = null;
            if (root == null)
            {
                sounds = null;
                fighterLabel.Text = "(no fighter)";
                Fill();
                status.Text = "Open a fighter folder (Fighter..).";
                return;
            }
            try
            {
                Cursor = Cursors.WaitCursor;
                string picked = Runtime.GetSettingText("SoundDataFolder", "");
                SoundTips.PickedData = picked;
                sounds = FighterSounds.Load(root, picked);
                SoundTips.Current = sounds;
            }
            catch (Exception ex)
            {
                sounds = null;
                status.Text = "Couldn't load " + root + ": " + ex.Message;
            }
            finally { Cursor = Cursors.Default; }
            adder = sounds != null ? new SoundAdder(sounds) : null;
            UpdateChanges();
            fighterLabel.Text = sounds != null ? sounds.Name : "(no fighter)";
            Text = "Sound Effect Viewer - " + (sounds != null ? sounds.Name + " (" + sounds.Root + ")" : "");
            filling = true;
            bankFilter.Items.Clear();
            bankFilter.Items.Add("All banks");
            if (sounds != null)
                foreach (var k in sounds.Fighter.Banks.Select(b => sounds.Fighter.Kinds[b]).Distinct())
                    bankFilter.Items.Add(k);
            bankFilter.SelectedIndex = 0;
            commonBank.Items.Clear();
            if (sounds != null)
                foreach (var p in sounds.OtherCommonBanks())
                {
                    commonBank.Items.Add(new BankItem { Path = p });
                    if (sounds.CommonBankPath != null && p.Equals(sounds.CommonBankPath, StringComparison.OrdinalIgnoreCase))
                        commonBank.SelectedIndex = commonBank.Items.Count - 1;
                }
            filling = false;
            Fill();
            if (sounds != null)
                status.Text = string.Format(CultureInfo.InvariantCulture, "{0}: {1} sounds in {2} banks; {3} common sounds. Double-click (or Play) to hear one; type in Alias to name it.",
                    sounds.Name, sounds.Fighter.Entries.Count, sounds.Fighter.Banks.Count, sounds.Common != null ? sounds.Common.Entries.Count : 0);
        }

        /// <summary>
        /// The filter (both tabs, as you type, case doesn't matter): a match anywhere in the tone name, your alias, the
        /// bank kind, or the sound ID: hex with or without 0x, any part of it ("0768", "5B", "0x7680061", "0x0768005B"),
        /// or the ID in decimal (124256353). Empty: everything.
        /// </summary>
        public static bool Matches(SoundEntry e, string f)
        {
            f = (f ?? "").Trim();
            if (f.Length == 0) return true;
            if (e.Name.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0 || e.Alias.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0 ||
                e.Kind.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0)
                return true;
            if (!e.Id.HasValue) return false;
            uint id = e.Id.Value;
            string hex = f.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? f.Substring(2) : f;
            if (hex.Length > 0 && hex.All(Uri.IsHexDigit))
            {
                // padded (0768005B) or not (768005B); "0x0768005B" and "0x768005B" both find it
                string full = id.ToString("X8", CultureInfo.InvariantCulture), bare = id.ToString("X", CultureInfo.InvariantCulture);
                string h = hex.ToUpperInvariant();
                if (full.Contains(h) || bare.Contains(h))
                    return true;
            }
            return f.All(char.IsDigit) && id.ToString(CultureInfo.InvariantCulture).Contains(f);
        }

        /// <summary>Fills both lists and the Banks tab (with the filter).</summary>
        public void Fill()
        {
            string f = filter.Text.Trim();
            string bank = bankFilter.SelectedIndex > 0 ? (string)bankFilter.SelectedItem : null;
            // the picked sound stays picked when it is still in the list (filtering as you type)
            var keepF = RowEntry(fighterGrid);
            var keepC = RowEntry(commonGrid);
            var fighterEntries = new List<SoundEntry>();
            if (sounds != null)
            {
                fighterEntries.AddRange(sounds.Fighter.Entries);
                if (adder != null && adder.Pending.Count > 0)
                {
                    // the new sounds after their bank's last id (where they will be once saved)
                    int at = fighterEntries.FindLastIndex(x => x.Bank == adder.Target && x.Id.HasValue) + 1;
                    fighterEntries.InsertRange(at > 0 ? at : fighterEntries.Count, adder.PendingEntries());
                }
            }
            FillGrid(fighterGrid, fighterEntries.Where(e => (bank == null || e.Kind == bank) && Matches(e, f)));
            FillGrid(commonGrid, sounds != null && sounds.Common != null ? sounds.Common.Entries.Where(e => Matches(e, f)) : Enumerable.Empty<SoundEntry>());
            Reselect(fighterGrid, keepF);
            Reselect(commonGrid, keepC);
            int allF = sounds != null ? sounds.Fighter.Entries.Count + (adder != null ? adder.Pending.Count : 0) : 0, allC = sounds != null && sounds.Common != null ? sounds.Common.Entries.Count : 0;
            fighterTab.Text = "Fighter sounds (" + (fighterGrid.Rows.Count == allF ? allF.ToString(CultureInfo.InvariantCulture) : fighterGrid.Rows.Count + " of " + allF) + ")";
            commonTab.Text = "Common sounds (" + (commonGrid.Rows.Count == allC ? allC.ToString(CultureInfo.InvariantCulture) : commonGrid.Rows.Count + " of " + allC) + ")";
            bool joucyu = sounds != null && sounds.CommonBank != null &&
                          Path.GetFileName(sounds.CommonBank.Path).Equals(FighterSounds.CommonBankFile, StringComparison.OrdinalIgnoreCase);
            commonNote.Text = sounds == null || sounds.CommonBank == null ? "No common bank found: pick the game's data folder (Game data..)." :
                joucyu ? "Row 0: every fighter's scripts play these with the same commands, e.g. Sound_Effect(SFX=0x46)." :
                         "Not the common bank: listed for reference (a fighter's script plays only banks loaded in the match).";
            var lines = new List<string>();
            if (sounds != null)
            {
                lines.Add("Fighter: " + sounds.Root);
                lines.AddRange(sounds.Notes);
                lines.Add("");
                lines.Add("Fighter banks:");
                lines.AddRange(sounds.Fighter.Notes.Select(x => "  " + x));
                if (sounds.Common != null)
                {
                    lines.Add("");
                    lines.Add("Common tab: " + (sounds.CommonBank != null ? sounds.CommonBank.Path : "-"));
                    lines.AddRange(sounds.Common.Notes.Select(x => "  " + x));
                }
                lines.Add("");
                lines.Add("Aliases: " + SoundAliases.FileFor(sounds.Name) + " and " + SoundAliases.FileFor(SoundAliases.CommonSet));
            }
            banksText.Text = string.Join(Environment.NewLine, lines.ToArray());
            ShowInfo();
        }

        void FillGrid(DataGridView g, IEnumerable<SoundEntry> entries)
        {
            g.SuspendLayout();
            g.Rows.Clear();
            var rows = new List<DataGridViewRow>();
            foreach (var e in entries)
            {
                var r = new DataGridViewRow();
                r.CreateCells(g);
                var t = e.Tone;
                bool audio = t != null && t.HasAudio;
                r.Cells[0].Value = e.IdText;
                r.Cells[1].Value = e.Name;
                r.Cells[2].Value = e.Alias;
                r.Cells[3].Value = e.Kind;
                r.Cells[4].Value = audio ? t.Seconds.ToString("0.000", CultureInfo.InvariantCulture) : "";
                r.Cells[5].Value = audio ? (t.Loops ? "loop" : "") : "";
                r.Cells[6].Value = audio ? t.Channels.ToString(CultureInfo.InvariantCulture) : "";
                r.Cells[7].Value = audio ? t.SampleRate.ToString(CultureInfo.InvariantCulture) : "";
                r.Cells[8].Value = t != null && t.DataBlock >= 0 ? t.VolumeDb.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture) : "";
                r.Cells[9].Value = t != null ? t.Index.ToString(CultureInfo.InvariantCulture) : "";
                r.Cells[10].Value = e.Note.Length > 0 ? e.Note : (t != null && !audio ? t.Kind.ToString().ToLowerInvariant() + ": nothing to play" : t != null && t.Codec != "IDSP" ? "codec " + t.Codec + ": not decoded" : "");
                r.Cells[2].ReadOnly = !e.Id.HasValue;
                r.Cells[8].ReadOnly = g.Columns[8].ReadOnly || t == null || t.DataBlock < 0;
                float was;
                if (adder != null && t != null && adder.VolumeEdits.TryGetValue(t, out was))
                {
                    r.Cells[8].Style.BackColor = Color.FromArgb(255, 220, 160);
                    r.Cells[10].Value = string.Format(CultureInfo.InvariantCulture, "volume {0:+0.0;-0.0;0.0} -> {1:+0.0;-0.0;0.0} dB (unsaved)", was, t.VolumeDb) + (e.Note.Length > 0 ? "; " + e.Note : "");
                }
                if (e.Pending != null)
                {
                    r.DefaultCellStyle.BackColor = Color.FromArgb(220, 240, 255);
                    r.DefaultCellStyle.Font = new Font(g.Font, FontStyle.Bold);
                }
                if (!e.Id.HasValue || !e.Playable) r.DefaultCellStyle.ForeColor = Color.Gray;
                r.Tag = e;
                rows.Add(r);
            }
            g.Rows.AddRange(rows.ToArray());
            g.ResumeLayout();
        }

        static SoundEntry RowEntry(DataGridView g)
        {
            var r = g.CurrentRow ?? (g.SelectedRows.Count > 0 ? g.SelectedRows[0] : null);
            return r != null ? r.Tag as SoundEntry : null;
        }

        static void Reselect(DataGridView g, SoundEntry e)
        {
            if (e == null) return;
            foreach (DataGridViewRow r in g.Rows)
                if (r.Tag == e)
                {
                    try { g.CurrentCell = r.Cells["Name"]; } catch (Exception) { }
                    return;
                }
        }

        DataGridView CurrentGrid { get { return tabs.SelectedTab == commonTab ? commonGrid : fighterGrid; } }

        /// <summary>The picked sound (the list of the tab shown; the fighter's list when on Banks).</summary>
        public SoundEntry Selected
        {
            get
            {
                var g = CurrentGrid;
                var r = g.CurrentRow ?? (g.SelectedRows.Count > 0 ? g.SelectedRows[0] : null);
                return r != null ? r.Tag as SoundEntry : null;
            }
        }

        string SelectedCommand { get { return Commands[Math.Max(0, command.SelectedIndex)][0]; } }

        void ShowInfo()
        {
            var e = Selected;
            bool any = e != null && e.Id.HasValue;
            addToScript.Enabled = copyId.Enabled = copyLine.Enabled = any;
            play.Enabled = e != null && e.Playable;
            info.Text = e == null ? "" : Describe(e);
        }

        /// <summary>The info line under the list for an entry.</summary>
        public static string Describe(SoundEntry e)
        {
            var t = e.Tone;
            var s = string.Format(CultureInfo.InvariantCulture, "{0}  {1}", e.IdText, e.Name);
            if (e.Id.HasValue)
                s += string.Format(CultureInfo.InvariantCulture, "   row 0x{0:X} label {1}", e.Row, e.Label);
            if (t != null)
                s += string.Format(CultureInfo.InvariantCulture, " -> tone {0} of {1} (BINF {2}, id {3})", t.Index, Path.GetFileName(e.Bank.Path), e.Bank.Name, e.Bank.Id);
            if (t != null && t.HasAudio)
            {
                s += string.Format(CultureInfo.InvariantCulture, "\n{0}{1}, {2}, {3} Hz, {4} samples ({5:0.000} s), {6}; volume {7:+0.0;-0.0;0.0} dB; PACK 0x{8:X} + 0x{9:X}",
                    t.Codec, t.Codec == "IDSP" ? " (DSP-ADPCM)" : "", t.Channels == 1 ? "mono" : t.Channels == 2 ? "stereo" : t.Channels + " channels", t.SampleRate, t.Samples, t.Seconds,
                    t.Loops ? string.Format(CultureInfo.InvariantCulture, "loops {0} - {1}", t.LoopStart, t.LoopEnd) : "one-shot", t.VolumeDb, t.DataOffset, t.DataSize);
                if (t.Loops)
                    s += "\nIt loops: Transient_Sound_Effect (PLAY_STATUS) holds it until the status ends; Stop_Sound_Effect stops it.";
            }
            if (e.Note.Length > 0) s += "\n" + e.Note;
            if (e.Pending != null)
                s += "\nNew, not saved yet (Save writes it): " + Path.GetFileName(e.Pending.Source) + ": " + e.Pending.How;
            string alias = e.Alias;
            if (alias.Length > 0) s += "\nAlias: " + alias;
            return s;
        }

        void AliasEdited(DataGridView g, int row, int col)
        {
            if (row < 0 || g.Columns[col].Name != "Alias") return;
            var e = g.Rows[row].Tag as SoundEntry;
            if (e == null || !e.Id.HasValue) return;
            string text = Convert.ToString(g.Rows[row].Cells[col].Value ?? "", CultureInfo.InvariantCulture);
            try
            {
                e.Alias = text;
                status.Text = "Alias saved: " + SoundAliases.FileFor(e.AliasSet);
            }
            catch (Exception ex) { status.Text = "Couldn't save the alias: " + ex.Message; }
            ShowInfo();
        }

        /// <summary>v1.7.33: a Volume cell typed in: the tone's TONE volume (dB), saved with Save (only that float changes).</summary>
        void VolumeEdited(DataGridView g, int row, int col)
        {
            if (row < 0 || g.Columns[col].Name != "Volume" || g.Columns[col].ReadOnly || adder == null) return;
            var e = g.Rows[row].Tag as SoundEntry;
            if (e == null || e.Tone == null || e.Tone.DataBlock < 0) return;
            string text = Convert.ToString(g.Rows[row].Cells[col].Value ?? "", CultureInfo.InvariantCulture).Trim().TrimStart('+');
            double v;
            if (!double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out v) && !double.TryParse(text, out v))
            {
                status.Text = "Volume: a number of dB (e.g. -3.5).";
                BeginInvoke((Action)Fill);
                return;
            }
            v = Math.Max(-40, Math.Min(20, v));
            SetToneVolume(e.Tone, (float)v);
            status.Text = string.Format(CultureInfo.InvariantCulture, "{0}: volume {1:+0.0;-0.0;0.0} dB (unsaved: Save writes it)", e.Tone.Name, v);
            BeginInvoke((Action)Fill);
        }

        /// <summary>v1.7.33: a tone's volume changed (the Volume column; the tests).</summary>
        public void SetToneVolume(Tone t, float db)
        {
            adder.SetVolume(t, db);
            UpdateChanges();
        }

        void UpdateChanges()
        {
            bool any = adder != null && adder.HasChanges;
            save.Enabled = saveTo.Enabled = discard.Enabled = any;
            addSounds.Enabled = adder != null;
            if (adder != null && any)
                status.Text = string.Format(CultureInfo.InvariantCulture, "Unsaved: {0} new sound(s), {1} volume change(s). Save writes them (backups first); Save to.. writes them into a folder to install.",
                    adder.Pending.Count, adder.VolumeEdits.Count);
        }

        /// <summary>v1.7.33: Add sounds.. (the dialog; AdderDialogHook fills it in the tests).</summary>
        public void ShowAdder()
        {
            if (adder == null) return;
            var dlg = new SoundAdderDialog(adder, (wav, name) => PlayWav(wav, name), StopPlaying);
            if (AdderDialogHook != null) { dlg.Show(this); AdderDialogHook(dlg); dlg.Close(); }
            else dlg.ShowDialog(this);
            dlg.Dispose();
            adder.Plan();
            Fill();
            UpdateChanges();
        }

        /// <summary>v1.7.33: writes the changes (outRoot null: in place; else under outRoot as the game's data).</summary>
        public SoundAdder.Saved SaveChanges(string outRoot)
        {
            if (adder == null || !adder.HasChanges) return null;
            StopPlaying();
            SoundAdder.Output built;
            try { built = adder.Build(); }
            catch (Exception ex) { status.Text = "Not saved: " + ex.Message; MessageBox.Show(this, ex.Message, "Not saved", MessageBoxButtons.OK, MessageBoxIcon.Error); return null; }
            if (!built.Ok)
            {
                status.Text = "Not saved: " + built.Problems[0];
                MessageBox.Show(this, "Not saved:\n" + string.Join("\n", built.Problems.Take(20).ToArray()), "Sound Adder", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
            string where = outRoot ?? sounds.Root;
            string msg = "Write these into " + where + "?\n\n" + string.Join("\n", built.Checks.ToArray()) +
                         (outRoot == null ? "\n\nEach file replaced is backed up first (FILE.yyyyMMdd-HHmmss.bak)." : "");
            bool go = ConfirmSave != null ? ConfirmSave(msg) : MessageBox.Show(this, msg, "Save sounds", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) == DialogResult.OK;
            if (!go) return null;
            SoundAdder.Saved saved;
            try { saved = adder.Save(outRoot); }
            catch (Exception ex)
            {
                status.Text = "Not saved: " + ex.Message;
                MessageBox.Show(this, ex.Message, "Not saved", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
            LoadFighter(saved.FighterRoot);
            status.Text = "Saved: " + string.Join(", ", saved.Written.ToArray()) + (saved.Backups.Count > 0 ? " (backups: " + saved.Backups.Count + ")" : "");
            return saved;
        }

        void SaveTo()
        {
            using (var dlg = new FolderBrowserDialog { Description = "A folder to write the sounds into, laid out as the game's data (fighter\\NAME\\sound, sound\\config): ready to install" })
            {
                var last = Runtime.GetSettingText("SoundSaveFolder", "");
                if (last.Length > 0) dlg.SelectedPath = last;
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                try { Runtime.SetSettingText("SoundSaveFolder", dlg.SelectedPath); } catch (Exception) { }
                SaveChanges(dlg.SelectedPath);
            }
        }

        /// <summary>Plays a WAV (the adder's preview).</summary>
        bool PlayWav(byte[] wav, string name)
        {
            try
            {
                StopPlaying();
                playing = new MemoryStream(wav);
                player = new SoundPlayer(playing);
                player.Play();
                status.Text = "Playing " + name;
                return true;
            }
            catch (Exception ex) { status.Text = "Couldn't play " + name + ": " + ex.Message; return false; }
        }

        /// <summary>The line Add to Script / Copy Line give: Sound_Effect(SFX=0x7680061).</summary>
        public static string CommandLine(string commandName, uint id)
        {
            uint crc;
            string param = "SFX";
            int count = 1;
            if (ACMD_INFO.TryGetIdent(commandName, out crc))
            {
                string syn;
                if (ACMD_INFO.PARAM_SYNTAX.TryGetValue(crc, out syn) && !string.IsNullOrEmpty(syn) && syn != "NONE")
                {
                    var names = syn.Split(',').Select(x => x.Trim()).ToArray();
                    param = names[0];
                    count = names.Length;
                }
                commandName = ACMD_INFO.CMD_NAMES[crc];
            }
            var parts = new List<string> { string.Format(CultureInfo.InvariantCulture, "{0}=0x{1:X}", param, id) };
            for (int i = 1; i < count; i++) parts.Add("0");
            return commandName + "(" + string.Join(", ", parts.ToArray()) + ")";
        }

        /// <summary>Where Add to Script writes, instead of the open script's editor (the tests: FastColoredTextBox can't be
        /// made under Mono); true when the line went in.</summary>
        public Func<string, bool> InsertLine;

        void AddToScript()
        {
            var e = Selected;
            if (e == null || !e.Id.HasValue) return;
            string line = CommandLine(SelectedCommand, e.Id.Value);
            if (InsertLine != null)
            {
                if (InsertLine(line)) status.Text = "Added: " + line;
                return;
            }
            var editor = activeEditor != null ? activeEditor() : null;
            if (editor == null)
            {
                MessageBox.Show(this, "Open an ACMD script first (the line goes below its caret). Copy Line puts it on the clipboard instead.\n\n" + line,
                    "No script open", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            editor.InsertCommandLine(line);
            status.Text = "Added: " + line;
            var form = editor.FindForm();
            if (form != null) form.Activate();
            editor.Focus();
        }

        /// <summary>The WAV a preview of the entry plays (the bank's volume, the gain, a looping tone's loop repeated).</summary>
        public byte[] PreviewWav(SoundEntry e)
        {
            var clip = Idsp.Decode(e.Bank.ReadAudio(e.Tone));
            double db = (double)gain.Value + (bankVolume.Checked ? e.Tone.VolumeDb : 0);
            var pcm = Idsp.Preview(clip, db, loop.Checked ? 8.0 : 0);
            return Idsp.Wav(pcm, clip.Channels, clip.SampleRate);
        }

        void Play()
        {
            var e = Selected;
            if (e == null) return;
            if (!e.Playable)
            {
                status.Text = e.Name + ": nothing to play" + (e.Tone != null && e.Tone.HasAudio ? " (codec " + e.Tone.Codec + ")" : "") + ".";
                return;
            }
            try
            {
                var wav = PreviewWav(e);
                StopPlaying();
                playing = new MemoryStream(wav);
                player = new SoundPlayer(playing);
                player.Play();          // (asynchronous: returns at once)
                status.Text = "Playing " + e.IdText + " " + e.Name + string.Format(CultureInfo.InvariantCulture, " ({0:0.00} s)", e.Tone.Seconds);
            }
            catch (Exception ex) { status.Text = "Couldn't play " + e.Name + ": " + ex.Message; }
        }

        void StopPlaying()
        {
            try { if (player != null) player.Stop(); } catch (Exception) { }
            if (player != null) player.Dispose();
            player = null;
            if (playing != null) playing.Dispose();
            playing = null;
        }

        /// <summary>v1.7.33: true when there is nothing unsaved, or the user drops it.</summary>
        public bool ConfirmDrop()
        {
            return adder == null || !adder.HasChanges ||
                   MessageBox.Show(this, "The new sounds / volume changes aren't saved. Drop them?", "Sound Effect Viewer", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes;
        }

        void PickFighter()
        {
            if (!ConfirmDrop()) return;
            using (var dlg = new FolderBrowserDialog { Description = "The fighter's folder (fighter\\NAME, with its sound folder)" })
            {
                if (sounds != null) dlg.SelectedPath = sounds.Root;
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                string root = FighterSounds.FindFighterRoot(Path.Combine(dlg.SelectedPath, "x")) ?? dlg.SelectedPath;
                if (Path.GetFileName(root).Equals("sound", StringComparison.OrdinalIgnoreCase)) root = Path.GetDirectoryName(root);
                LoadFighter(root);
            }
        }

        void PickData()
        {
            using (var dlg = new FolderBrowserDialog { Description = "The game's data folder (it holds sound\\config\\soundlabeltable.bin and sound\\se\\snd_se_joucyu.nus3bank)" })
            {
                var cur = Runtime.GetSettingText("SoundDataFolder", "");
                if (cur.Length > 0) dlg.SelectedPath = cur;
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                bool p;
                var stb = FighterSounds.FindData(null, Path.Combine(Path.Combine("sound", "config"), "soundlabeltable.bin"), dlg.SelectedPath, out p);
                var cmn = FighterSounds.FindData(null, Path.Combine(Path.Combine("sound", "se"), FighterSounds.CommonBankFile), dlg.SelectedPath, out p);
                if (stb == null && cmn == null)
                {
                    MessageBox.Show(this, "No sound\\config\\soundlabeltable.bin or sound\\se\\snd_se_joucyu.nus3bank there.", "Game data", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return;
                }
                Runtime.SetSettingText("SoundDataFolder", dlg.SelectedPath);
                LoadFighter(sounds != null ? sounds.Root : null);
            }
        }
    }
}
