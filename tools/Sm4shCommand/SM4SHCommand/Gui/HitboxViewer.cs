using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Linq;
using System.Windows.Forms;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Viewer;

namespace Sm4shCommand.GUI
{
    /// <summary>
    /// Tools > Hitbox Viewer: the open game script's hitboxes on the fighter's own model and animation,
    /// frame by frame, with a knockback / hitstun calculator (Sm4sh-Calculator's formulas) for the
    /// hitbox picked in the list. It follows edits to the script as you type.
    /// </summary>
    public class HitboxViewer : Form
    {
        readonly FighterAssets assets;
        readonly ITS_EDITOR editor;
        readonly uint scriptCrc;
        readonly Func<uint, IList<ICommand>> getScript;
        List<FrameState> frames = new List<FrameState>();
        Omo anim;
        string animName;

        readonly Viewport view = new Viewport { Dock = DockStyle.Fill };
        readonly TrackBar bar = new TrackBar { Dock = DockStyle.Fill, Minimum = 1, Maximum = 1, TickStyle = TickStyle.None };
        readonly Label frameLabel = new Label { AutoSize = true, Padding = new Padding(4, 6, 4, 0) };
        readonly Button play = new Button { Text = "Play", Width = 56 };
        readonly Timer timer = new Timer { Interval = 33 };
        readonly Timer editTimer = new Timer { Interval = 400 };
        readonly ComboBox animBox = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 260 };
        readonly CheckBox ifTrue = new CheckBox { Text = "If conditions true", Checked = true, AutoSize = true };
        readonly CheckBox frameSpeed = new CheckBox { Text = "Frame speed", Checked = true, AutoSize = true };
        readonly CheckBox showModel = new CheckBox { Text = "Model", Checked = true, AutoSize = true };
        readonly CheckBox showBones = new CheckBox { Text = "Bones", AutoSize = true };
        readonly CheckBox showAngles = new CheckBox { Text = "Angles", Checked = true, AutoSize = true };
        readonly Label status = new Label { Dock = DockStyle.Bottom, Height = 18, ForeColor = Color.DimGray };
        readonly DataGridView grid = new DataGridView
        {
            Dock = DockStyle.Fill, ReadOnly = true, AllowUserToAddRows = false, AllowUserToDeleteRows = false,
            RowHeadersVisible = false, SelectionMode = DataGridViewSelectionMode.FullRowSelect, MultiSelect = false,
            AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.AllCells,
        };
        readonly ComboBox target = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 140 };
        readonly NumericUpDown targetPct = Num(0, 999, 0), attackerPct = Num(0, 999, 0), charge = Num(0, 60, 0),
            stale = Num(0, 9, 0), kbMult = Num(0, 10, 1, 2), launchRate = Num(0, 10, 1, 2), diAngle = Num(0, 359, 0);
        readonly CheckBox crouch = new CheckBox { Text = "Crouching", AutoSize = true };
        readonly CheckBox aerial = new CheckBox { Text = "Target in the air", AutoSize = true };
        readonly CheckBox useDI = new CheckBox { Text = "DI at", AutoSize = true };
        readonly TextBox results = new TextBox { Multiline = true, ReadOnly = true, Dock = DockStyle.Fill, ScrollBars = ScrollBars.Vertical, Font = new Font(FontFamily.GenericMonospace, 8.5f) };

        static NumericUpDown Num(decimal min, decimal max, decimal val, int dec = 1)
        {
            return new NumericUpDown { Minimum = min, Maximum = max, Value = val, DecimalPlaces = dec, Width = 70, Increment = dec > 1 ? 0.05m : 1 };
        }

        public HitboxViewer(FighterAssets assets, ITS_EDITOR editor, uint scriptCrc, string title, Func<uint, IList<ICommand>> getScript)
        {
            this.assets = assets;
            this.editor = editor;
            this.scriptCrc = scriptCrc;
            this.getScript = getScript;
            Text = "Hitbox Viewer - " + title;
            Size = new Size(1150, 720);
            StartPosition = FormStartPosition.CenterParent;
            view.Assets = assets;
            Build();
            foreach (var f in FighterAttributes.Load()) target.Items.Add(f);
            target.SelectedIndex = Math.Max(0, target.Items.Cast<FighterAttributes>().ToList().FindIndex(x => x.Name == "Mario"));
            animBox.Items.Add("(none)");
            foreach (var n in assets.AnimationNames) animBox.Items.Add(n);
            animName = assets.AnimationFor(scriptCrc);
            animBox.SelectedItem = animName ?? "(none)";
            animBox.SelectedIndexChanged += (o, e) => { animName = animBox.SelectedIndex <= 0 ? null : (string)animBox.SelectedItem; Rerun(); };
            timer.Tick += (o, e) => { bar.Value = bar.Value >= bar.Maximum ? bar.Minimum : bar.Value + 1; };
            editTimer.Tick += (o, e) => { editTimer.Stop(); Rerun(); };
            if (editor != null)
                editor.TextChanged += Editor_TextChanged;
            FormClosed += (o, e) => { timer.Stop(); if (editor != null) editor.TextChanged -= Editor_TextChanged; };
            Rerun();
        }

        void Editor_TextChanged(object sender, EventArgs e) { editTimer.Stop(); editTimer.Start(); }

        void Build()
        {
            var tools = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 30, WrapContents = false };
            tools.Controls.AddRange(new Control[] { new Label { Text = "Animation:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, animBox,
                ifTrue, frameSpeed, showModel, showBones, showAngles });
            var bottom = new TableLayoutPanel { Dock = DockStyle.Bottom, Height = 34, ColumnCount = 5 };
            var prev = new Button { Text = "<", Width = 30 };
            var next = new Button { Text = ">", Width = 30 };
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            bottom.Controls.Add(prev, 0, 0);
            bottom.Controls.Add(play, 1, 0);
            bottom.Controls.Add(next, 2, 0);
            bottom.Controls.Add(bar, 3, 0);
            bottom.Controls.Add(frameLabel, 4, 0);
            prev.Click += (o, e) => { if (bar.Value > bar.Minimum) bar.Value--; };
            next.Click += (o, e) => { if (bar.Value < bar.Maximum) bar.Value++; };
            play.Click += (o, e) => { timer.Enabled = !timer.Enabled; play.Text = timer.Enabled ? "Pause" : "Play"; };
            bar.ValueChanged += (o, e) => ShowFrame();

            var left = new Panel { Dock = DockStyle.Fill };
            left.Controls.Add(view);
            left.Controls.Add(tools);
            left.Controls.Add(bottom);
            left.Controls.Add(status);

            var calc = new TableLayoutPanel { Dock = DockStyle.Top, ColumnCount = 4, AutoSize = true, Padding = new Padding(4) };
            Action<string, Control, string, Control> row = (l1, c1, l2, c2) =>
            {
                calc.Controls.Add(new Label { Text = l1, AutoSize = true, Padding = new Padding(0, 5, 0, 0) });
                calc.Controls.Add(c1);
                calc.Controls.Add(new Label { Text = l2, AutoSize = true, Padding = new Padding(0, 5, 0, 0) });
                calc.Controls.Add(c2 ?? new Label());
            };
            row("Target", target, "Target %", targetPct);
            row("Attacker % (rage)", attackerPct, "Charge frames", charge);
            row("Stale (times used)", stale, "KB multiplier", kbMult);
            row("Launch rate", launchRate, "", null);
            var flags = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            flags.Controls.AddRange(new Control[] { crouch, aerial, useDI, diAngle, new Label { Text = "deg", AutoSize = true, Padding = new Padding(0, 5, 0, 0) } });
            calc.Controls.Add(flags);
            calc.SetColumnSpan(flags, 4);
            foreach (Control c in new Control[] { target, targetPct, attackerPct, charge, stale, kbMult, launchRate, diAngle, crouch, aerial, useDI })
            {
                if (c is NumericUpDown) ((NumericUpDown)c).ValueChanged += (o, e) => Calc();
                else if (c is CheckBox) ((CheckBox)c).CheckedChanged += (o, e) => Calc();
                else if (c is ComboBox) ((ComboBox)c).SelectedIndexChanged += (o, e) => Calc();
            }
            var right = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 200 };
            right.Panel1.Controls.Add(grid);
            var calcGroup = new GroupBox { Text = "Knockback / hitstun (pick a hitbox above)", Dock = DockStyle.Fill };
            calcGroup.Controls.Add(results);
            calcGroup.Controls.Add(calc);
            right.Panel2.Controls.Add(calcGroup);
            grid.SelectionChanged += (o, e) =>
            {
                view.SelectedHitbox = grid.SelectedRows.Count > 0 ? (int)grid.SelectedRows[0].Cells[0].Value : -1;
                Calc();
            };

            var split = new SplitContainer { Dock = DockStyle.Fill, FixedPanel = FixedPanel.Panel2 };
            Load += (o, e) =>
            {
                split.SplitterDistance = Math.Max(200, split.Width - 450);
                right.SplitterDistance = Math.Max(80, right.Height - 330);
            };
            split.Panel1.Controls.Add(left);
            split.Panel2.Controls.Add(right);
            Controls.Add(split);
            foreach (var c in new[] { ifTrue, frameSpeed })
                c.CheckedChanged += (o, e) => Rerun();
            showModel.CheckedChanged += (o, e) => { view.ShowModel = showModel.Checked; view.Recompute(); };
            showBones.CheckedChanged += (o, e) => { view.ShowBones = showBones.Checked; view.Invalidate(); };
            showAngles.CheckedChanged += (o, e) => { view.ShowAngles = showAngles.Checked; view.Invalidate(); };
            var meshes = new Button { Text = "Meshes..", AutoSize = true };
            meshes.Click += (o, e) => PickMeshes();
            tools.Controls.Add(meshes);
        }

        void PickMeshes()
        {
            using (var f = new Form { Text = "Meshes shown", Size = new Size(320, 480), StartPosition = FormStartPosition.CenterParent })
            {
                var list = new CheckedListBox { Dock = DockStyle.Fill, CheckOnClick = true };
                foreach (var m in assets.Model.Meshes) list.Items.Add(m.Name, m.Visible);
                f.Controls.Add(list);
                f.ShowDialog(this);
                for (int i = 0; i < assets.Model.Meshes.Count; i++)
                    assets.Model.Meshes[i].Visible = list.GetItemChecked(i);
                view.Invalidate();
            }
        }

        IList<ICommand> CurrentCommands(out string error)
        {
            error = null;
            if (editor != null)
            {
                try
                {
                    var lines = ACMDCompiler.StripComments(editor.Lines.ToArray());
                    return ACMDCompiler.CompileCommands(lines.ToArray()).Cast<ICommand>().ToList();
                }
                catch (Exception ex)
                {
                    error = ex.Message.Split('\n')[0];
                }
            }
            return getScript(scriptCrc);
        }

        void Rerun()
        {
            string error;
            var cmds = CurrentCommands(out error);
            anim = assets.GetAnimation(animName);
            int length = anim != null ? anim.Frames : 0;
            var runner = new HitboxRunner { ConditionsTrue = ifTrue.Checked, UseFrameSpeed = frameSpeed.Checked, GetScript = getScript };
            // enough game frames for the whole animation (slowed down by Set_Frame_Duration), or 120
            var probe = runner.Run(cmds ?? new List<ICommand>(), 600);
            int n = probe.Count;
            if (length > 0)
            {
                int end = probe.FindIndex(f => f.AnimFrame >= length - 1);
                n = end >= 0 ? end + 1 : 600;
            }
            else
            {
                int last = probe.FindLastIndex(f => f.Hitboxes.Count > 0);
                n = Math.Max(60, last + 20);
            }
            frames = probe.Take(Math.Max(1, n)).ToList();
            int keep = bar.Value;
            bar.Maximum = Math.Max(1, frames.Count);
            bar.Value = Math.Min(Math.Max(keep, 1), bar.Maximum);
            view.Animation = anim;
            status.Text = (error != null ? "Doesn't compile (showing the last saved script): " + error + "   " : "") +
                          (animName != null ? animName + ", " + length + " frames" : "No animation found for this script: pick one above") +
                          (cmds == null ? "   (no game script)" : "");
            ShowFrame();
        }

        void ShowFrame()
        {
            if (frames.Count == 0) return;
            var f = frames[Math.Min(bar.Value, frames.Count) - 1];
            view.Frame = f;
            view.AnimFrame = Math.Max(0, f.AnimFrame);
            view.Recompute();
            frameLabel.Text = string.Format(CultureInfo.InvariantCulture, "frame {0} / {1}   anim {2:0.##}", f.GameFrame, frames.Count, f.AnimFrame + 1);
            int sel = view.SelectedHitbox;
            grid.SuspendLayout();
            grid.Rows.Clear();
            if (grid.Columns.Count == 0)
                foreach (var c in new[] { "ID", "Damage", "Angle", "KBG", "WBKB", "BKB", "Size", "Bone", "Hitlag", "SDI", "Effect", "Command" })
                    grid.Columns.Add(c, c);
            foreach (var h in f.Hitboxes)
            {
                int r = grid.Rows.Add(h.Id, h.Damage, h.Angle, h.KBG, h.WBKB, h.BKB, h.Size, "0x" + h.Bone.ToString("X"), h.Hitlag, h.SDI, h.Effect, h.Command);
                var hc = Viewport.HitboxColors[((h.Id % 8) + 8) % 8];   // a light tint (cells can't be see-through)
                grid.Rows[r].DefaultCellStyle.BackColor = Color.FromArgb(255 - (255 - hc.R) * 3 / 10, 255 - (255 - hc.G) * 3 / 10, 255 - (255 - hc.B) * 3 / 10);
            }
            grid.ClearSelection();
            foreach (DataGridViewRow r in grid.Rows)
                if ((int)r.Cells[0].Value == sel) r.Selected = true;
            if (grid.SelectedRows.Count == 0 && grid.Rows.Count > 0 && sel < 0)
                grid.Rows[0].Selected = true;
            grid.ResumeLayout();
            view.SelectedHitbox = grid.SelectedRows.Count > 0 ? (int)grid.SelectedRows[0].Cells[0].Value : sel;
            Calc();
        }

        void Calc()
        {
            var f = frames.Count > 0 ? frames[Math.Min(bar.Value, frames.Count) - 1] : null;
            var hb = f == null ? null : f.Hitboxes.Find(x => x.Id == view.SelectedHitbox);
            if (hb == null)
            {
                results.Text = f == null || f.Hitboxes.Count == 0 ? "No hitboxes on this frame." : "Pick a hitbox in the list.";
                view.Trajectory = null;
                view.Invalidate();
                return;
            }
            var inp = new KnockbackInput
            {
                Hitbox = hb, Target = target.SelectedItem as FighterAttributes, TargetPercent = (float)targetPct.Value,
                AttackerPercent = (float)attackerPct.Value, StaleCount = (int)stale.Value, ChargeFrames = (float)charge.Value,
                Crouching = crouch.Checked, TargetAerial = aerial.Checked, KbMultiplier = (float)kbMult.Value,
                LaunchRate = (float)launchRate.Value, UseDI = useDI.Checked, DIAngle = (float)diAngle.Value,
            };
            var r = KnockbackCalc.Calculate(inp);
            int firstFrame = frames.FindIndex(x => x.Hitboxes.Any(y => y.Id == hb.Id)) + 1;
            var end = r.Path[Math.Min(r.Hitstun, r.Path.Count - 1)];
            var ic = CultureInfo.InvariantCulture;
            results.Text = string.Join("\r\n", new[] {
                string.Format(ic, "Hitbox {0}: {1:0.##}% , angle {2}, BKB {3}, KBG {4}{5}", hb.Id, hb.Damage, hb.Angle, hb.BKB, hb.KBG, hb.WBKB != 0 ? ", WBKB " + hb.WBKB : ""),
                string.Format(ic, "Damage dealt       {0:0.###}% (stale x{1:0.###})", r.Damage, r.StaleMultiplier),
                string.Format(ic, "Target's % after   {0:0.###}%", r.TargetPercentAfter),
                string.Format(ic, "Knockback          {0:0.###}{1}", r.KB, r.Tumble ? "  (tumble)" : ""),
                string.Format(ic, "Launch angle       {0:0.##} deg{1}", r.Angle, r.Spike ? "  (spike)" : ""),
                string.Format(ic, "Launch speed       {0:0.###}  (x {1:0.###}, y {2:0.###})", r.LaunchSpeed, r.LaunchSpeedX, r.LaunchSpeedY),
                string.Format(ic, "Hitstun            {0} frames  (target acts on frame {1})", r.Hitstun, r.Faf),
                string.Format(ic, "Hitstun cancel     airdodge {0}, aerial {1}", r.AirdodgeCancel, r.AerialCancel),
                string.Format(ic, "Hitlag             attacker {0}, target {1}", r.AttackerHitlag, r.TargetHitlag),
                string.Format(ic, "Shield             stun {0}, hitlag {1}", r.ShieldStun, r.ShieldHitlag),
                string.Format(ic, "Distance           {0:0.##} forward, {1:0.##} up at the end of hitstun", end[0], end[1]),
                firstFrame > 0 ? string.Format(ic, "Comes out on game frame {0}", firstFrame) : "",
                "Formulas: Sm4sh-Calculator (rubendal). Trajectory: no stage, dashed in the view.",
            });
            view.Trajectory = r.Path;
            view.Invalidate();
        }
    }
}
