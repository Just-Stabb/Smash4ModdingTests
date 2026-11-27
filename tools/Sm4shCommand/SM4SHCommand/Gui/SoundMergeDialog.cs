using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using Sm4shCommand.Sound;

namespace Sm4shCommand.GUI
{
    /// <summary>
    /// The Sound Effect Viewer's "Merge sound mods.." (v1.7.34, Sound.SoundMerger): two or more sound mods (folders or
    /// .zips, each with its own sound\config\soundlabeltable.bin and its fighters' banks) merged against the base (the
    /// game's soundlabeltable.bin, from the Game data folder) into a new install folder, so every mod's added sounds keep
    /// working. Check shows what the merge would do (the report) without writing; Merge writes the folder and its
    /// MERGE_REPORT.txt.
    /// </summary>
    public class SoundMergeDialog : Form
    {
        readonly TextBox baseBox = new TextBox { Width = 560 };
        readonly Button baseBrowse = new Button { Text = "Browse..", AutoSize = true };
        readonly ListBox mods = new ListBox { Dock = DockStyle.Fill, IntegralHeight = false, HorizontalScrollbar = true };
        readonly Button addFolder = new Button { Text = "Add folder..", AutoSize = true };
        readonly Button addZip = new Button { Text = "Add .zip..", AutoSize = true };
        readonly Button remove = new Button { Text = "Remove", AutoSize = true };
        readonly Button up = new Button { Text = "Up", AutoSize = true };
        readonly Button down = new Button { Text = "Down", AutoSize = true };
        readonly TextBox outBox = new TextBox { Width = 560 };
        readonly Button outBrowse = new Button { Text = "Browse..", AutoSize = true };
        readonly ComboBox policy = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 330 };
        readonly CheckBox rewrite = new CheckBox { Text = "Rewrite the mods' scripts to their new ids", AutoSize = true, Checked = true };
        readonly CheckBox unbanked = new CheckBox { Text = "Take rows a mod changed without shipping their banks", AutoSize = true };
        readonly CheckBox copyAll = new CheckBox { Text = "Copy the mods' other files too (a complete install folder)", AutoSize = true };
        readonly Button check = new Button { Text = "Check", AutoSize = true };
        readonly Button run = new Button { Text = "Merge", AutoSize = true };
        readonly Button openOut = new Button { Text = "Open folder", AutoSize = true, Enabled = false };
        readonly Button close = new Button { Text = "Close", AutoSize = true, DialogResult = DialogResult.Cancel };
        readonly TextBox report = new TextBox { Multiline = true, ReadOnly = true, Dock = DockStyle.Fill, ScrollBars = ScrollBars.Both, WordWrap = false, Font = new Font(FontFamily.GenericMonospace, 8.5f) };
        readonly Label status = new Label { Dock = DockStyle.Bottom, Height = 20, ForeColor = Color.DimGray, AutoEllipsis = true, Padding = new Padding(4, 3, 4, 0) };
        readonly ToolTip tips = new ToolTip();
        readonly string startFolder;

        public TextBox BaseBox { get { return baseBox; } }
        public ListBox Mods { get { return mods; } }
        public TextBox OutBox { get { return outBox; } }
        public ComboBox Policy { get { return policy; } }
        public CheckBox Rewrite { get { return rewrite; } }
        public TextBox ReportBox { get { return report; } }
        public MergeResult Last { get; private set; }

        public SoundMergeDialog(string baseTable, string startFolder)
        {
            this.startFolder = startFolder;
            Text = "Merge sound mods";
            Size = new Size(1000, 720);
            StartPosition = FormStartPosition.CenterParent;
            baseBox.Text = baseTable ?? "";

            var intro = new Label
            {
                Dock = DockStyle.Top, Height = 48, Padding = new Padding(6, 4, 6, 0), ForeColor = Color.DimGray,
                Text = "The game has one sound\\config\\soundlabeltable.bin: two mods that add sounds each ship their own, and the one installed last loses the other's new sounds. " +
                       "This merges them against the base: each fighter's row from the mod that changed it; the same fighter changed by several mods: its banks merged, " +
                       "the later mod's new ids moved after the earlier's (remapped, its scripts rewritten). Nothing is changed in place: it writes a new folder.",
            };
            var grid = new TableLayoutPanel { Dock = DockStyle.Top, Height = 64, ColumnCount = 3, Padding = new Padding(4, 2, 4, 0) };
            grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            baseBox.Anchor = outBox.Anchor = AnchorStyles.Left | AnchorStyles.Right;
            grid.Controls.Add(new Label { Text = "Base (the game's soundlabeltable.bin):", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, 0, 0);
            grid.Controls.Add(baseBox, 1, 0);
            grid.Controls.Add(baseBrowse, 2, 0);
            grid.Controls.Add(new Label { Text = "Output folder (new / empty):", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, 0, 1);
            grid.Controls.Add(outBox, 1, 1);
            grid.Controls.Add(outBrowse, 2, 1);

            var modPanel = new Panel { Dock = DockStyle.Top, Height = 168, Padding = new Padding(6, 2, 6, 2) };
            var modButtons = new FlowLayoutPanel { Dock = DockStyle.Right, Width = 110, FlowDirection = FlowDirection.TopDown, WrapContents = false };
            foreach (var b in new[] { addFolder, addZip, remove, up, down }) { b.Width = 100; b.Height = 26; b.AutoSize = false; b.Margin = new Padding(3, 2, 3, 2); modButtons.Controls.Add(b); }
            modPanel.Controls.Add(mods);
            modPanel.Controls.Add(modButtons);
            modPanel.Controls.Add(new Label { Text = "Mods, in order (the first wins a conflict unless \"take the later mod's\"):", Dock = DockStyle.Top, Height = 18 });

            var opts = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 58, Padding = new Padding(4, 2, 4, 0) };
            opts.Controls.Add(new Label { Text = "When two mods change the same thing:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) });
            opts.Controls.Add(policy);
            opts.Controls.Add(rewrite);
            opts.Controls.Add(unbanked);
            opts.Controls.Add(copyAll);
            policy.Items.Add("keep the first mod's (report the conflict)");
            policy.Items.Add("take the later mod's (report the conflict)");
            policy.SelectedIndex = 0;

            var buttons = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 34, Padding = new Padding(4, 3, 4, 0) };
            foreach (var b in new[] { check, run, openOut, close }) buttons.Controls.Add(b);

            Controls.Add(report);
            Controls.Add(buttons);
            Controls.Add(opts);
            Controls.Add(modPanel);
            Controls.Add(grid);
            Controls.Add(intro);
            Controls.Add(status);
            CancelButton = close;

            tips.SetToolTip(baseBox, "The soundlabeltable.bin the mods were made from: the game's own (your Game data folder's sound\\config).\n" +
                                     "Its data folder's fighter\\NAME\\sound banks, when there, tell which mod changed an existing tone's volume.");
            tips.SetToolTip(addFolder, "A mod's folder (laid out as the game's data somewhere inside: INSTALL_TO_data, content\\patch\\data, data ...).");
            tips.SetToolTip(addZip, "A mod's .zip (stored or deflated; unzipped to a temporary folder for the merge).");
            tips.SetToolTip(check, "Shows what the merge would do (rows, banks, id remaps, scripts, conflicts, warnings) without writing anything.");
            tips.SetToolTip(run, "Writes the merged install folder and its MERGE_REPORT.txt.");
            tips.SetToolTip(rewrite, "The later mod's new sounds get new ids when they move after the earlier mod's: rewrite its ACMD scripts\n" +
                                     "(script\\animcmd\\*\\*.bin, weapons too) to them (only sound commands' id parameters change).");
            tips.SetToolTip(unbanked, "A mod made from another soundlabeltable.bin changes rows it has no bank for. Off: the base's are kept (and reported).");

            baseBrowse.Click += (o, e) =>
            {
                using (var d = new OpenFileDialog { Filter = "soundlabeltable.bin|soundlabeltable.bin|All files|*.*", Title = "The base soundlabeltable.bin (the game's)" })
                    if (d.ShowDialog(this) == DialogResult.OK) baseBox.Text = d.FileName;
            };
            outBrowse.Click += (o, e) =>
            {
                using (var d = new FolderBrowserDialog { Description = "A new or empty folder for the merged mod" })
                {
                    if (outBox.Text.Length > 0 && Directory.Exists(outBox.Text)) d.SelectedPath = outBox.Text;
                    if (d.ShowDialog(this) == DialogResult.OK) outBox.Text = d.SelectedPath;
                }
            };
            addFolder.Click += (o, e) =>
            {
                using (var d = new FolderBrowserDialog { Description = "A sound mod's folder" })
                {
                    if (startFolder != null && Directory.Exists(startFolder)) d.SelectedPath = startFolder;
                    if (d.ShowDialog(this) == DialogResult.OK) AddMod(d.SelectedPath);
                }
            };
            addZip.Click += (o, e) =>
            {
                using (var d = new OpenFileDialog { Filter = "Zip files|*.zip", Multiselect = true, Title = "Sound mods (.zip)" })
                    if (d.ShowDialog(this) == DialogResult.OK) foreach (var f in d.FileNames) AddMod(f);
            };
            remove.Click += (o, e) => { if (mods.SelectedIndex >= 0) mods.Items.RemoveAt(mods.SelectedIndex); };
            up.Click += (o, e) => Move(-1);
            down.Click += (o, e) => Move(1);
            check.Click += (o, e) => RunMerge(true);
            run.Click += (o, e) => RunMerge(false);
            openOut.Click += (o, e) => { try { System.Diagnostics.Process.Start(outBox.Text); } catch (Exception) { } };
            status.Text = "Add two or more mods, pick an output folder, then Check (nothing written) or Merge.";
        }

        public void AddMod(string path)
        {
            if (!mods.Items.Cast<string>().Any(x => string.Equals(x, path, StringComparison.OrdinalIgnoreCase))) mods.Items.Add(path);
            if (outBox.Text.Length == 0)
            {
                var parent = Path.GetDirectoryName(path.TrimEnd('\\', '/'));
                if (parent != null) outBox.Text = Path.Combine(parent, "merged_sound_mods");
            }
        }

        void Move(int d)
        {
            int i = mods.SelectedIndex, j = i + d;
            if (i < 0 || j < 0 || j >= mods.Items.Count) return;
            var x = mods.Items[i];
            mods.Items.RemoveAt(i);
            mods.Items.Insert(j, x);
            mods.SelectedIndex = j;
        }

        public MergeOptions Options()
        {
            return new MergeOptions { LaterWins = policy.SelectedIndex == 1, RewriteScripts = rewrite.Checked, TakeUnbankedRows = unbanked.Checked, CopyOtherFiles = copyAll.Checked };
        }

        /// <summary>Check (dryRun) or Merge: the report shown; Merge writes the output folder.</summary>
        public MergeResult RunMerge(bool dryRun)
        {
            string outDir = dryRun ? null : outBox.Text.Trim();
            if (!dryRun && outDir.Length == 0) { status.Text = "Pick an output folder."; return null; }
            Cursor = Cursors.WaitCursor;
            try
            {
                var m = new SoundMerger(baseBox.Text.Trim(), mods.Items.Cast<string>(), Options(), FighterSounds.LoadBankAliases(FighterSounds.BankAliasesPath)) { Version = Program.Version };
                var r = m.Run(outDir);
                Last = r;
                report.Text = r.Report;
                openOut.Enabled = !dryRun && r.Ok;
                status.Text = !r.Ok ? "Not merged: " + r.Errors[0] :
                    (dryRun ? "Check: " : "Merged into " + outDir + ": ") + r.RowsFrom.Count + " row(s) from the mods, " + r.MergedBanks.Count + " bank(s) merged, " + r.Remaps.Count + " id(s) remapped, " +
                    r.RewrittenScripts.Count + " script(s) rewritten, " + r.Conflicts.Count + " conflict(s), " + r.Warnings.Count + " warning(s)" + (dryRun ? " (nothing written)." : ". See MERGE_REPORT.txt.");
                return r;
            }
            finally { Cursor = Cursors.Default; }
        }
    }
}
