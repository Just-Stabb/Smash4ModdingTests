using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
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
        readonly CheckBox showTextures = new CheckBox { Text = "Textures", Checked = true, AutoSize = true };
        readonly CheckBox showEnemy = new CheckBox { Text = "Enemy", Checked = true, AutoSize = true };
        FighterAssets enemy;
        string enemyStand, enemyHurt, enemyFly;
        uint currentCrc;
        bool filling;           // the grid is being refilled (ShowFrame)        // the script shown: the open one, or the one for the animation picked
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
            currentCrc = scriptCrc;
            animName = assets.AnimationFor(scriptCrc);
            animBox.SelectedItem = animName ?? "(none)";
            animBox.SelectedIndexChanged += (o, e) =>
            {
                animName = animBox.SelectedIndex <= 0 ? null : (string)animBox.SelectedItem;
                currentCrc = ScriptFor(animName);
                Rerun();
            };
            LoadEnemy(Runtime.GetSettingText("ViewerEnemyFolder", ""), false);
            timer.Tick += (o, e) => { bar.Value = bar.Value >= bar.Maximum ? bar.Minimum : bar.Value + 1; };
            editTimer.Tick += (o, e) => { editTimer.Stop(); Rerun(); };
            if (editor != null)
                editor.TextChanged += Editor_TextChanged;
            FormClosed += (o, e) => { timer.Stop(); if (editor != null) editor.TextChanged -= Editor_TextChanged; };
            Rerun();
        }

        void Editor_TextChanged(object sender, EventArgs e) { editTimer.Stop(); editTimer.Start(); }

        /// <summary>The game script that plays an animation: the open script if it does, else the
        /// first script named for it that game.bin has, else none (0).</summary>
        uint ScriptFor(string anim)
        {
            if (anim == null) return scriptCrc;
            var list = assets.ScriptsFor(anim);
            if (list.Contains(scriptCrc) || anim == assets.AnimationFor(scriptCrc)) return scriptCrc;
            foreach (var crc in list)
                if (getScript(crc) != null) return crc;
            return 0;
        }

        /// <summary>The enemy's model: the folder given (remembered), else Mario's next to this
        /// fighter's folder (fighter/mario). The calculator's target follows it when the names match.</summary>
        void LoadEnemy(string folder, bool remember)
        {
            string dir = folder;
            if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir))
                dir = Path.Combine(Path.GetDirectoryName(assets.Root) ?? "", "mario");
            enemy = null;
            try
            {
                string root = FighterAssets.FindRoot(dir);
                if (root != null && root != assets.Root)
                    enemy = FighterAssets.Load(root);
            }
            catch (Exception ex) { status.Text = "Couldn't load the enemy model: " + ex.Message; }
            if (enemy != null)
            {
                enemyStand = enemy.FindAnimation("Wait1", "Wait", "Wait2");
                enemyHurt = enemy.FindAnimation("DamageN2", "DamageN1", "DamageHi2", "DamageHi1");
                enemyFly = enemy.FindAnimation("DamageFlyN", "DamageFlyHi", "DamageFlyTop", "DamageFlyLw");
                if (remember) Runtime.SetSettingText("ViewerEnemyFolder", enemy.Root);
                string key = Simple(enemy.Name);
                foreach (FighterAttributes f in target.Items)
                    if (Simple(f.Name) == key) { target.SelectedItem = f; break; }
            }
            showEnemy.Text = enemy != null ? "Enemy (" + enemy.Name + ")" : "Enemy (none: Enemy model..)";
        }

        static string Simple(string name)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in (name ?? "").ToLowerInvariant()) if (char.IsLetterOrDigit(c)) sb.Append(c);
            return sb.ToString();
        }

        void PickEnemy()
        {
            using (var dlg = new FolderBrowserDialog { Description = "The enemy fighter's folder (with model and motion), e.g. fighter\\mario" })
            {
                if (enemy != null) dlg.SelectedPath = enemy.Root;
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                LoadEnemy(dlg.SelectedPath, true);
                if (enemy == null)
                    MessageBox.Show(this, "No model / motion folders found there.", "Enemy model", MessageBoxButtons.OK, MessageBoxIcon.Information);
                Calc();
            }
        }

        void Build()
        {
            var tools = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 58, WrapContents = true };
            tools.Controls.AddRange(new Control[] { new Label { Text = "Animation:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, animBox,
                ifTrue, frameSpeed, showModel, showTextures, showBones, showAngles, showEnemy });
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
                if (filling) return;
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
            showTextures.CheckedChanged += (o, e) => { view.ShowTextures = showTextures.Checked; view.Invalidate(); };
            showEnemy.CheckedChanged += (o, e) => Calc();
            var meshes = new Button { Text = "Meshes..", AutoSize = true };
            meshes.Click += (o, e) => PickMeshes();
            var enemyButton = new Button { Text = "Enemy model..", AutoSize = true };
            enemyButton.Click += (o, e) => PickEnemy();
            tools.Controls.Add(meshes);
            tools.Controls.Add(enemyButton);
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
            if (currentCrc == 0) return null;
            if (currentCrc != scriptCrc) return getScript(currentCrc);
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
            Text = "Hitbox Viewer - " + (currentCrc == 0 ? "(no script)" : Runtime.ScriptLabel(currentCrc)) +
                   (currentCrc != scriptCrc && currentCrc != 0 ? " (saved game.bin; edits follow the open script only)" : "");
            status.Text = (error != null ? "Doesn't compile (showing the last saved script): " + error + "   " : "") +
                          (animName != null ? animName + ", " + length + " frames" : "No animation found for this script: pick one above") +
                          (cmds == null ? "   (no game script for this animation: no hitboxes)" : "");
            ShowFrame();
        }

        void ShowFrame()
        {
            if (frames.Count == 0) return;
            var f = frames[Math.Min(bar.Value, frames.Count) - 1];
            view.Frame = f;
            view.AnimFrame = Math.Max(0, f.AnimFrame);
            frameLabel.Text = string.Format(CultureInfo.InvariantCulture, "frame {0} / {1}   anim {2:0.##}", f.GameFrame, frames.Count, f.AnimFrame + 1);
            int sel = view.SelectedHitbox;
            filling = true;
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
            filling = false;
            view.SelectedHitbox = grid.SelectedRows.Count > 0 ? (int)grid.SelectedRows[0].Cells[0].Value : sel;
            Calc();
        }

        /// <summary>The picked hitbox (on this frame, or where it last came out before it) and the game
        /// frame it hits on: the first frame of that run of frames.</summary>
        HitboxData PickedHitbox(int current, out int hitFrame)
        {
            hitFrame = -1;
            int id = view.SelectedHitbox;
            if (id < 0 || frames.Count == 0) return null;
            int at = -1;
            for (int i = Math.Min(current, frames.Count - 1); i >= 0; i--)
                if (frames[i].Hitboxes.Any(x => x.Id == id)) { at = i; break; }
            if (at < 0) at = frames.FindIndex(f => f.Hitboxes.Any(x => x.Id == id));
            if (at < 0) return null;
            while (at > 0 && frames[at - 1].Hitboxes.Any(x => x.Id == id)) at--;
            hitFrame = at + 1;
            return frames[at].Hitboxes.Find(x => x.Id == id);
        }

        void Calc()
        {
            int cur = frames.Count > 0 ? Math.Min(bar.Value, frames.Count) - 1 : -1;
            int hitFrame = -1;
            var hb = cur < 0 ? null : PickedHitbox(cur, out hitFrame);
            if (hb == null)
            {
                results.Text = cur < 0 || frames[cur].Hitboxes.Count == 0 ? "No hitboxes on this frame." : "Pick a hitbox in the list.";
                view.Trajectory = null;
                view.TrajectoryOrigin = null;
                PlaceEnemy(null, 0, cur + 1, null);
                view.Recompute();
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
            ScriptModifiers.Apply(r, hitFrame, frames.SelectMany(f => f.Writes));
            var end = r.Path[Math.Min(r.Hitstun, r.Path.Count - 1)];
            int frozen = r.TargetStops.Sum(x => x[1]);
            var ic = CultureInfo.InvariantCulture;
            bool changed = r.FinalHitstun != r.Hitstun || r.FinalTargetHitlag != r.TargetHitlag || r.FinalAttackerHitlag != r.AttackerHitlag;
            var lines = new List<string> {
                string.Format(ic, "Hitbox {0}: {1:0.##}% , angle {2}, BKB {3}, KBG {4}{5}", hb.Id, hb.Damage, hb.Angle, hb.BKB, hb.KBG, hb.WBKB != 0 ? ", WBKB " + hb.WBKB : ""),
                string.Format(ic, "Damage dealt       {0:0.###}% (stale x{1:0.###})", r.Damage, r.StaleMultiplier),
                string.Format(ic, "Target's % after   {0:0.###}%", r.TargetPercentAfter),
                string.Format(ic, "Knockback          {0:0.###}{1}", r.KB, r.Tumble ? "  (tumble)" : ""),
                string.Format(ic, "Launch angle       {0:0.##} deg{1}", r.Angle, r.Spike ? "  (spike)" : ""),
                string.Format(ic, "Launch speed       {0:0.###}  (x {1:0.###}, y {2:0.###})", r.LaunchSpeed, r.LaunchSpeedX, r.LaunchSpeedY),
                string.Format(ic, "Hitstun            {0} frames  (target acts on frame {1}{2})", r.FinalHitstun,
                    r.FinalHitstun == 0 ? 0 : r.FinalHitstun + frozen + 1, frozen > 0 ? ", after " + frozen + " frames of hitstop during it" : ""),
                string.Format(ic, "Hitstun cancel     airdodge {0}, aerial {1}", r.AirdodgeCancel, r.AerialCancel),
                string.Format(ic, "Hitlag             attacker {0}, target {1}  (hitlag x{2:0.##})", r.FinalAttackerHitlag, r.FinalTargetHitlag, hb.Hitlag),
                string.Format(ic, "Shield             stun {0}, hitlag {1}", r.ShieldStun, r.ShieldHitlag),
                string.Format(ic, "Distance           {0:0.##} forward, {1:0.##} up at the end of hitstun", end[0], end[1]),
                string.Format(ic, "Hits on game frame {0}", hitFrame),
            };
            if (r.ScriptNotes.Count > 0)
            {
                lines.Add("");
                lines.Add("The script's modifiers:");
                lines.AddRange(r.ScriptNotes.Select(x => "  " + x));
                if (changed)
                    lines.Add(string.Format(ic, "  Without them: hitstun {0}, hitlag attacker {1}, target {2}", r.Hitstun, r.AttackerHitlag, r.TargetHitlag));
            }
            lines.Add("");
            lines.Add("Formulas: Sm4sh-Calculator (rubendal). Trajectory: no stage, dashed in the view.");
            results.Text = string.Join("\r\n", lines.ToArray());
            view.Trajectory = r.Path;
            PlaceEnemy(hb, hitFrame, cur + 1, r);
            view.Recompute();
        }

        /// <summary>Puts the enemy where the hitbox hits it (on the ground, or at the hitbox's height
        /// in the air), standing until the hit, then in hitlag, then along the trajectory with its
        /// damage animation. Real time: the attacker's script waits out its hitlag.</summary>
        void PlaceEnemy(HitboxData hb, int hitFrame, int frame, KnockbackResult r)
        {
            view.TrajectoryOrigin = null;
            if (enemy == null || !showEnemy.Checked) { view.Enemy = null; return; }
            float z0 = 14, y0 = 0;
            if (hb != null)
            {
                var pos = HitboxPosition(hb, hitFrame);
                if (pos != null)
                {
                    z0 = Math.Max(4, pos[2] + hb.Size * 0.6f);   // its front in the hitbox
                    if (aerial.Checked) y0 = Math.Max(0, pos[1] - 6);
                }
            }
            var e = new EnemyFigure { Assets = enemy, Z = z0, Y = y0 };
            e.Animation = enemy.GetAnimation(enemyStand);
            if (e.Animation != null && e.Animation.Frames > 0) e.Frame = frame % e.Animation.Frames;
            if (hb != null && r != null && frame >= hitFrame)
            {
                int real = frame == hitFrame ? frame : frame + r.FinalAttackerHitlag;
                int launch = hitFrame + r.FinalTargetHitlag;
                var damage = enemy.GetAnimation(r.Tumble ? enemyFly ?? enemyHurt : enemyHurt ?? enemyFly);
                if (damage != null) e.Animation = damage;
                if (real < launch)
                {
                    e.Frame = 0;
                    e.Z += (real & 1) == 0 ? 0.35f : -0.35f;     // shaking in hitlag
                }
                else
                {
                    int k = real - launch;
                    foreach (var stop in r.TargetStops)
                        if (k > stop[0]) k -= Math.Min(stop[1], k - stop[0]);
                    var p = r.Path[Math.Min(k, r.Path.Count - 1)];
                    e.Z += p[0];
                    e.Y = Math.Max(0, e.Y + p[1]);
                    e.Frame = e.Animation != null ? Math.Min(k, Math.Max(0, e.Animation.Frames - 1)) : 0;
                }
            }
            view.Enemy = e;
            view.TrajectoryOrigin = new[] { 0f, y0, z0 };
        }

        /// <summary>The hitbox's world position on game frame (x, y, z).</summary>
        float[] HitboxPosition(HitboxData hb, int gameFrame)
        {
            if (gameFrame < 1 || gameFrame > frames.Count) return null;
            var world = assets.Skeleton.World(anim, Math.Max(0, frames[gameFrame - 1].AnimFrame));
            int bi = assets.Skeleton.ScriptBone(hb.Bone);
            if (bi < 0 || bi >= world.Length) return null;
            return world[bi].ClearScale().Transform(hb.X, hb.Y, hb.Z);
        }
    }
}
