using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using Sm4shCommand.Sound;

namespace Sm4shCommand.GUI
{
    /// <summary>
    /// The Sound Effect Viewer's "Add sounds.." (v1.7.33, the Sound Adder): audio files added to one of the fighter's
    /// banks as new tones, each with its tone name (the bank's prefix filled in), alias, volume (dB, the TONE volume),
    /// silence trimming, normalising and looping, previewed as the game will play it (encoded to DSP-ADPCM and decoded
    /// back, at its volume). The sounds stay pending (new / unsaved rows in the viewer's list) until the viewer's Save.
    /// </summary>
    public class SoundAdderDialog : Form
    {
        readonly SoundAdder adder;
        readonly Func<byte[], string, bool> playWav;
        readonly Action stopPlaying;
        readonly ComboBox bank = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 420 };
        readonly CheckBox costumes = new CheckBox { Text = "Also the costume banks on this row", AutoSize = true, Checked = true };
        readonly Button addFiles = new Button { Text = "Add files..", AutoSize = true };
        readonly Button remove = new Button { Text = "Remove", AutoSize = true };
        readonly Label formats = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 34, ForeColor = Color.DimGray, Padding = new Padding(6, 2, 6, 0) };
        readonly DataGridView grid = new DataGridView
        {
            Dock = DockStyle.Fill, AllowUserToAddRows = false, AllowUserToDeleteRows = false, RowHeadersVisible = false,
            SelectionMode = DataGridViewSelectionMode.FullRowSelect, MultiSelect = false, AllowUserToResizeRows = false,
            EditMode = DataGridViewEditMode.EditOnKeystrokeOrF2,
        };
        readonly TrackBar volumeBar = new TrackBar { Minimum = -400, Maximum = 200, TickFrequency = 50, SmallChange = 5, LargeChange = 10, Width = 260, AutoSize = false, Height = 28 };
        readonly NumericUpDown volume = new NumericUpDown { Minimum = -40, Maximum = 20, DecimalPlaces = 1, Increment = 0.5m, Width = 64 };
        readonly NumericUpDown threshold = new NumericUpDown { Minimum = -90, Maximum = -10, DecimalPlaces = 0, Increment = 1, Value = -45, Width = 54 };
        readonly Button preview = new Button { Text = "Preview", AutoSize = true };
        readonly Button stop = new Button { Text = "Stop", AutoSize = true };
        readonly Label info = new Label { Dock = DockStyle.Fill, AutoEllipsis = true, Padding = new Padding(6, 2, 6, 2) };
        readonly Label plan = new Label { Dock = DockStyle.Fill, AutoEllipsis = true, Padding = new Padding(6, 2, 6, 2), ForeColor = Color.DarkRed };
        readonly Button close = new Button { Text = "Close", AutoSize = true, DialogResult = DialogResult.OK };
        readonly ToolTip tips = new ToolTip();
        bool filling;

        public SoundAdderDialog(SoundAdder adder, Func<byte[], string, bool> playWav, Action stopPlaying)
        {
            this.adder = adder;
            this.playWav = playWav;
            this.stopPlaying = stopPlaying;
            Text = "Add sounds - " + adder.Sounds.Name;
            Size = new Size(1100, 560);
            StartPosition = FormStartPosition.CenterParent;
            MinimizeBox = false;
            Build();
            FillBanks();
            Refill();
        }

        public DataGridView Grid { get { return grid; } }
        public ComboBox BankBox { get { return bank; } }
        public NumericUpDown VolumeBox { get { return volume; } }
        public TrackBar VolumeBar { get { return volumeBar; } }
        public Label PlanLabel { get { return plan; } }

        class BankItem
        {
            public Nus3Bank Bank;
            public string Text;
            public override string ToString() { return Text; }
        }

        void Build()
        {
            var top = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 32, WrapContents = false, Padding = new Padding(4, 3, 4, 0) };
            top.Controls.Add(new Label { Text = "Bank:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) });
            top.Controls.Add(bank);
            top.Controls.Add(costumes);
            top.Controls.Add(addFiles);
            top.Controls.Add(remove);
            Action<string, string, int, bool> col = (name, head, w, edit) =>
            {
                var c = new DataGridViewTextBoxColumn { Name = name, HeaderText = head, Width = w, ReadOnly = !edit, SortMode = DataGridViewColumnSortMode.NotSortable };
                if (edit) c.DefaultCellStyle.BackColor = Color.FromArgb(255, 255, 230);
                grid.Columns.Add(c);
            };
            Action<string, string> check = (name, head) =>
                grid.Columns.Add(new DataGridViewCheckBoxColumn { Name = name, HeaderText = head, Width = name == "Normalize" ? 66 : 44, SortMode = DataGridViewColumnSortMode.NotSortable });
            col("File", "File", 120, false);
            col("Name", "Tone name", 230, true);
            col("Alias", "Alias", 140, true);
            col("Volume", "Volume (dB)", 70, true);
            check("Trim", "Trim");
            check("Normalize", "Normalize");
            check("Loop", "Loop");
            col("Length", "Length (s)", 64, false);
            col("Ch", "Ch", 28, false);
            col("Id", "Sound ID", 86, false);
            col("Label", "Label", 44, false);
            col("Tone", "Tone #", 48, false);
            col("Status", "Status", 200, false);
            grid.Columns["Id"].DefaultCellStyle.Font = new Font(FontFamily.GenericMonospace, 8.5f);

            var sel = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 34, WrapContents = false, Padding = new Padding(4, 3, 4, 0) };
            sel.Controls.Add(new Label { Text = "Volume (dB):", AutoSize = true, Padding = new Padding(0, 7, 0, 0) });
            sel.Controls.Add(volumeBar);
            sel.Controls.Add(volume);
            sel.Controls.Add(new Label { Text = "Silence below (dBFS):", AutoSize = true, Padding = new Padding(14, 7, 0, 0) });
            sel.Controls.Add(threshold);
            sel.Controls.Add(preview);
            sel.Controls.Add(stop);
            var bottom = new Panel { Dock = DockStyle.Bottom, Height = 150 };
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 34, FlowDirection = FlowDirection.RightToLeft, Padding = new Padding(4, 3, 4, 0) };
            buttons.Controls.Add(close);
            buttons.Controls.Add(new Label
            {
                AutoSize = true, Padding = new Padding(0, 7, 12, 0), ForeColor = Color.DimGray,
                Text = "The sounds are pending (new / unsaved in the list) until Save in the viewer writes the bank and soundlabeltable.bin.",
            });
            var infoPanel = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 2, ColumnCount = 1 };
            infoPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 45));
            infoPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 55));
            infoPanel.Controls.Add(info, 0, 0);
            infoPanel.Controls.Add(plan, 0, 1);
            bottom.Controls.Add(infoPanel);
            bottom.Controls.Add(buttons);
            bottom.Controls.Add(sel);
            Controls.Add(grid);
            Controls.Add(formats);
            Controls.Add(top);
            Controls.Add(bottom);
            AcceptButton = close;
            formats.Text = "Formats: " + AudioImport.Capabilities() + " Every sound becomes 48000 Hz (resampled), mono or stereo as the file is, DSP-ADPCM (IDSP) as the game's own tones.";

            tips.SetToolTip(bank, "The fighter's bank the sounds go into. Their ids: the next labels of the row it plays from (row << 16 | label), new in the whole soundlabeltable.");
            tips.SetToolTip(costumes, "A player in costume NN loads the costume bank (snd_se_NAME_cNN) instead of the main one and plays the same ids from it:\n" +
                                      "with this on, the costume banks on the same row get the same tones at the same indexes (else the new ids are silent in those costumes).");
            tips.SetToolTip(addFiles, "Pick audio files (several at once). " + AudioImport.Capabilities());
            tips.SetToolTip(volumeBar, "The TONE volume (dB): what the game plays the tone at (vanilla tones -20 .. +6). Preview plays it at this volume.");
            tips.SetToolTip(volume, "The TONE volume (dB).");
            tips.SetToolTip(threshold, "Trim cuts the leading / trailing audio whose peak is below this (tools/gekkouga_sound.py's -45 dBFS).");
            tips.SetToolTip(preview, "Plays the sound as the game will have it: encoded to DSP-ADPCM, decoded back, at its volume (a looping one loops ~8 s).");

            addFiles.Click += (o, e) => PickFiles();
            remove.Click += (o, e) => RemoveSelected();
            preview.Click += (o, e) => Preview();
            stop.Click += (o, e) => { if (stopPlaying != null) stopPlaying(); };
            bank.SelectedIndexChanged += (o, e) =>
            {
                if (filling || bank.SelectedItem == null) return;
                var b = ((BankItem)bank.SelectedItem).Bank;
                if (b == adder.Target) return;
                var old = adder.Target;
                adder.Target = b;
                foreach (var p in adder.Pending)
                    if (old != null && p.ToneName.StartsWith(old.Name + "_", StringComparison.Ordinal))
                        p.ToneName = b.Name + p.ToneName.Substring(old.Name.Length);
                Refill();
            };
            costumes.CheckedChanged += (o, e) => { if (!filling) { adder.AlsoCostumes = costumes.Checked; Refill(); } };
            grid.SelectionChanged += (o, e) => ShowSelected();
            grid.CellEndEdit += (o, e) => CellEdited(e.RowIndex, e.ColumnIndex);
            grid.CurrentCellDirtyStateChanged += (o, e) =>
            {
                if (grid.IsCurrentCellDirty && grid.CurrentCell is DataGridViewCheckBoxCell) grid.CommitEdit(DataGridViewDataErrorContexts.Commit);
            };
            grid.CellValueChanged += (o, e) =>
            {
                if (filling || e.RowIndex < 0) return;
                var n = grid.Columns[e.ColumnIndex].Name;
                if (n == "Trim" || n == "Normalize" || n == "Loop") CellEdited(e.RowIndex, e.ColumnIndex);
            };
            grid.CellDoubleClick += (o, e) => { if (e.RowIndex >= 0 && grid.Columns[e.ColumnIndex].ReadOnly) Preview(); };
            volumeBar.Scroll += (o, e) => { if (!filling) SetVolume(volumeBar.Value / 10m); };
            volume.ValueChanged += (o, e) => { if (!filling) SetVolume(volume.Value); };
            threshold.ValueChanged += (o, e) =>
            {
                var p = Selected;
                if (filling || p == null) return;
                p.TrimDb = (double)threshold.Value;
                Refill();
            };
            FormClosing += (o, e) => { if (stopPlaying != null) stopPlaying(); };
        }

        void FillBanks()
        {
            filling = true;
            bank.Items.Clear();
            var s = adder.Sounds;
            foreach (var b in s.Fighter.Banks)
            {
                int row;
                s.Fighter.RowOfBank.TryGetValue(b, out row);
                string kind = s.Fighter.Kinds[b];
                string text = string.Format(CultureInfo.InvariantCulture, "{0}  {1}  ({2}, {3} tones)", kind, Path.GetFileName(b.Path),
                    row >= 0 && s.Table != null ? string.Format(CultureInfo.InvariantCulture, "row 0x{0:X}, {1} labels", row, s.Table.Labels(row).Length) : "no row: can't add", b.Tones.Count);
                bank.Items.Add(new BankItem { Bank = b, Text = text });
                if (b == adder.Target) bank.SelectedIndex = bank.Items.Count - 1;
            }
            costumes.Checked = adder.AlsoCostumes;
            filling = false;
        }

        /// <summary>Adds files (the Add files.. button's, the tests' without the file dialog).</summary>
        public void AddFiles(IEnumerable<string> files)
        {
            foreach (var f in files)
                adder.Pending.Add(new PendingSound { Source = f, ToneName = PendingSound.DefaultName(adder.Target, f) });
            Refill();
            if (grid.Rows.Count > 0)
            {
                filling = true;
                grid.CurrentCell = grid.Rows[grid.Rows.Count - 1].Cells["Name"];
                filling = false;
                ShowSelected();
            }
        }

        void PickFiles()
        {
            using (var dlg = new OpenFileDialog { Multiselect = true, Filter = AudioImport.FileFilter, Title = "Sounds to add to " + (adder.Target != null ? Path.GetFileName(adder.Target.Path) : "the bank") })
            {
                var last = Runtime.GetSettingText("SoundAddFolder", "");
                if (last.Length > 0 && Directory.Exists(last)) dlg.InitialDirectory = last;
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                try { Runtime.SetSettingText("SoundAddFolder", Path.GetDirectoryName(dlg.FileNames[0])); } catch (Exception) { }
                Cursor = Cursors.WaitCursor;
                try { AddFiles(dlg.FileNames); }
                finally { Cursor = Cursors.Default; }
            }
        }

        void RemoveSelected()
        {
            var p = Selected;
            if (p == null) return;
            adder.Pending.Remove(p);
            Refill();
        }

        public PendingSound Selected
        {
            get
            {
                var r = grid.CurrentRow ?? (grid.SelectedRows.Count > 0 ? grid.SelectedRows[0] : null);
                return r != null ? r.Tag as PendingSound : null;
            }
        }

        /// <summary>Plans again (labels, ids, tone indexes; reads / encodes what changed) and fills the list.</summary>
        public void Refill()
        {
            var keep = Selected;
            adder.Plan();
            filling = true;
            grid.Rows.Clear();
            foreach (var p in adder.Pending)
            {
                int i = grid.Rows.Add();
                var r = grid.Rows[i];
                r.Tag = p;
                r.Cells["File"].Value = Path.GetFileName(p.Source);
                r.Cells["Name"].Value = p.ToneName;
                r.Cells["Alias"].Value = p.Alias;
                r.Cells["Volume"].Value = p.VolumeDb.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture);
                r.Cells["Trim"].Value = p.Trim;
                r.Cells["Normalize"].Value = p.Normalize;
                r.Cells["Loop"].Value = p.Loop;
                bool ok = p.Idsp != null && p.Error == null;
                r.Cells["Length"].Value = p.Pcm != null ? p.Seconds.ToString("0.000", CultureInfo.InvariantCulture) : "";
                r.Cells["Ch"].Value = p.Pcm != null ? p.Channels.ToString(CultureInfo.InvariantCulture) : "";
                r.Cells["Id"].Value = p.Tone != null ? string.Format(CultureInfo.InvariantCulture, "0x{0:X8}", p.Id) : "";
                r.Cells["Label"].Value = p.Label >= 0 ? p.Label.ToString(CultureInfo.InvariantCulture) : "";
                r.Cells["Tone"].Value = p.ToneIndex >= 0 ? p.ToneIndex.ToString(CultureInfo.InvariantCulture) : "";
                r.Cells["Status"].Value = p.Error ?? (ok ? "new / unsaved" : "");
                if (p.Error != null) r.DefaultCellStyle.ForeColor = Color.DarkRed;
            }
            if (keep != null)
                foreach (DataGridViewRow r in grid.Rows)
                    if (r.Tag == keep) { grid.CurrentCell = r.Cells["Name"]; break; }
            filling = false;
            var lines = new List<string>(adder.PlanErrors);
            int row = adder.Row;
            if (adder.Target != null && row >= 0 && adder.Sounds.Table != null)
            {
                int count = adder.Sounds.Table.Labels(row).Length;
                lines.Add(string.Format(CultureInfo.InvariantCulture, "Row 0x{0:X} ({1}): {2} labels now; the new sounds get labels {2} - {3}, ids 0x{4:X8} - 0x{5:X8} (none of them in use anywhere in soundlabeltable.bin), tones {6} - {7}.",
                    row, Path.GetFileName(adder.Target.Path), count, count + Math.Max(0, adder.Pending.Count - 1), SoundLabelTable.SoundId(row, count),
                    SoundLabelTable.SoundId(row, count + Math.Max(0, adder.Pending.Count - 1)), adder.FirstToneIndex, adder.FirstToneIndex + Math.Max(0, adder.Pending.Count - 1)));
                var sharers = adder.RowSharers(FighterSounds.LoadBankAliases(FighterSounds.BankAliasesPath));
                if (sharers.Count > 0) lines.Add("The row is also played by " + string.Join(", ", sharers.ToArray()) + ": the new labels are new ids for them too (nothing played them).");
            }
            lines.AddRange(adder.PlanNotes);
            int costumeCount = adder.Target != null ? new SoundAdder(adder.Sounds, adder.Target) { AlsoCostumes = true }.Costumes().Count : 0;
            costumes.Text = "Also the costume banks on this row (" + costumeCount + ")";
            costumes.Enabled = costumeCount > 0;
            plan.Text = string.Join("\n", lines.ToArray());
            plan.ForeColor = adder.PlanErrors.Count > 0 ? Color.DarkRed : Color.DarkGreen;
            ShowSelected();
        }

        void ShowSelected()
        {
            var p = Selected;
            bool was = filling;
            filling = true;
            bool any = p != null;
            volume.Enabled = volumeBar.Enabled = threshold.Enabled = preview.Enabled = remove.Enabled = any;
            if (any)
            {
                volume.Value = Math.Max(volume.Minimum, Math.Min(volume.Maximum, (decimal)Math.Round(p.VolumeDb, 1)));
                volumeBar.Value = Math.Max(volumeBar.Minimum, Math.Min(volumeBar.Maximum, (int)Math.Round(p.VolumeDb * 10)));
                threshold.Value = Math.Max(threshold.Minimum, Math.Min(threshold.Maximum, (decimal)p.TrimDb));
                info.Text = p.Source + "\n" + (p.Error != null ? "Problem: " + p.Error : p.How + (p.Pcm != null ? string.Format(CultureInfo.InvariantCulture,
                    "; {0} samples ({1:0.000} s, {2:0.0} frames at 60 fps), IDSP {3} bytes", p.Samples, p.Seconds, p.Seconds * 60, p.Idsp.Length) : ""));
            }
            else info.Text = adder.Pending.Count == 0 ? "Add files.. picks the sounds to add." : "";
            filling = was;
        }

        void SetVolume(decimal db)
        {
            var p = Selected;
            if (p == null) return;
            p.VolumeDb = (float)db;
            if (p.Tone != null) p.Tone.VolumeDb = p.VolumeDb;
            bool was = filling;
            filling = true;
            volume.Value = Math.Max(volume.Minimum, Math.Min(volume.Maximum, db));
            volumeBar.Value = Math.Max(volumeBar.Minimum, Math.Min(volumeBar.Maximum, (int)Math.Round(db * 10)));
            if (grid.CurrentRow != null) grid.CurrentRow.Cells["Volume"].Value = p.VolumeDb.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture);
            filling = was;
        }

        void CellEdited(int row, int col)
        {
            if (filling || row < 0 || row >= grid.Rows.Count) return;
            var p = grid.Rows[row].Tag as PendingSound;
            if (p == null) return;
            var c = grid.Rows[row].Cells[col];
            string name = grid.Columns[col].Name, text = Convert.ToString(c.Value ?? "", CultureInfo.InvariantCulture).Trim();
            switch (name)
            {
                case "Name": p.ToneName = text; break;
                case "Alias": p.Alias = text; return;
                case "Volume":
                    double v;
                    if (double.TryParse(text.TrimStart('+'), NumberStyles.Float, CultureInfo.InvariantCulture, out v) || double.TryParse(text.TrimStart('+'), out v))
                        p.VolumeDb = (float)Math.Max(-40, Math.Min(20, v));
                    break;
                case "Trim": p.Trim = Convert.ToBoolean(c.Value); break;
                case "Normalize": p.Normalize = Convert.ToBoolean(c.Value); break;
                case "Loop": p.Loop = Convert.ToBoolean(c.Value); break;
                default: return;
            }
            BeginInvokeRefill();
        }

        bool refillQueued;

        void BeginInvokeRefill()
        {
            // (not inside the grid's own edit event: rebuilding its rows there throws); one at a time
            if (!IsHandleCreated) { Refill(); return; }
            if (refillQueued) return;
            refillQueued = true;
            BeginInvoke((Action)(() => { refillQueued = false; Refill(); }));
        }

        /// <summary>The WAV Preview plays: the IDSP decoded back, at the sound's volume (a looping one ~8 s).</summary>
        public static byte[] PreviewWav(PendingSound p)
        {
            var clip = Idsp.Decode(p.Idsp);
            var pcm = Idsp.Preview(clip, p.VolumeDb, p.Loop ? 8.0 : 0);
            return Idsp.Wav(pcm, clip.Channels, clip.SampleRate);
        }

        void Preview()
        {
            var p = Selected;
            if (p == null || p.Idsp == null) return;
            if (playWav != null) playWav(PreviewWav(p), p.ToneName);
        }
    }
}
