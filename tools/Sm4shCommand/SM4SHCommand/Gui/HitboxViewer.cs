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
        ITS_EDITOR editor;
        uint scriptCrc;
        readonly Func<uint, IList<ICommand>> getScript;
        // v1.5.0: the effect script (effect.bin's script of the same name, the open tab's effect editor while edited)
        Func<uint, IList<ICommand>> getEffect;
        ITS_EDITOR effectEditor;
        EffectLibrary library;
        List<EffectData> allEffects = new List<EffectData>();
        List<TrailData> allTrails = new List<TrailData>();
        string effectError;
        // v1.6.3: Markers and Labels off, HQ on by default; the three are reset to these once (an ini written by an
        // older version keeps the user's later choices after that)
        static readonly bool defaults163 = ResetDefaultsOnce();
        static HitboxViewer() { }   // (a static constructor: the reset runs before the first viewer's boxes read the settings)
        static bool ResetDefaultsOnce()
        {
            if (Runtime.GetSetting("ViewerDefaults163", false)) return false;
            Runtime.SetSetting("ViewerEffects", false);
            Runtime.SetSetting("ViewerEffectLabels", false);
            Runtime.SetSetting("ViewerFxQuality", true);
            Runtime.SetSetting("ViewerDefaults163", true);
            return true;
        }
        readonly CheckBox showEffects = new CheckBox { Text = "Markers", AutoSize = true, Checked = Runtime.GetSetting("ViewerEffects", false) };
        // v1.6.0 (Level 2): the effects drawn (particles, effect models, textured trails), their quality, a dark background
        readonly CheckBox showParticles = new CheckBox { Text = "Effects", AutoSize = true, Checked = Runtime.GetSetting("ViewerParticles", true) };
        readonly CheckBox fxQuality = new CheckBox { Text = "HQ", AutoSize = true, Checked = Runtime.GetSetting("ViewerFxQuality", true) };
        readonly CheckBox darkBg = new CheckBox { Text = "Dark bg", AutoSize = true, Checked = Runtime.GetSetting("ViewerDarkBg", true) };
        readonly CheckBox showLabels = new CheckBox { Text = "Labels", AutoSize = true, Checked = Runtime.GetSetting("ViewerEffectLabels", false) };
        readonly CheckBox showTrails = new CheckBox { Text = "Trails", AutoSize = true, Checked = Runtime.GetSetting("ViewerTrails", true) };
        readonly CheckBox flip = new CheckBox { Text = "Flip facing", AutoSize = true };
        // v1.6.2: hitboxes drawn or not, the body overlays; the model parts (meshes) tab; the expression script (its
        // visibility commands) followed as the game / effect scripts are
        readonly CheckBox showHitboxes = new CheckBox { Text = "Hitboxes", AutoSize = true, Checked = Runtime.GetSetting("ViewerHitboxes", true) };
        readonly CheckBox showOverlays = new CheckBox { Text = "Overlays", AutoSize = true, Checked = Runtime.GetSetting("ViewerOverlays", true) };
        readonly DataGridView partsGrid = new DataGridView
        {
            Dock = DockStyle.Fill, AllowUserToAddRows = false, AllowUserToDeleteRows = false, RowHeadersVisible = false,
            SelectionMode = DataGridViewSelectionMode.FullRowSelect, AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.AllCells,
        };
        readonly Label partsInfo = new Label { Dock = DockStyle.Bottom, Height = 54, AutoEllipsis = true };
        TabControl tabsRight;
        TabPage partsTab;
        bool partsFilling;
        Func<uint, IList<ICommand>> getExpression;
        ITS_EDITOR expressionEditor;
        static VisGroups visGroups = VisGroups.Load(Path.Combine(Application.StartupPath, "VisGroups.txt"),
                                                   Path.Combine(Application.StartupPath, "VisUser.txt"));
        // the parts tab's choices, per fighter, while the program runs
        static readonly Dictionary<string, Dictionary<string, bool>> partChoices = new Dictionary<string, Dictionary<string, bool>>(StringComparer.OrdinalIgnoreCase);
        Dictionary<string, bool> UserParts
        {
            get
            {
                Dictionary<string, bool> d;
                if (!partChoices.TryGetValue(assets.Root ?? "", out d)) partChoices[assets.Root ?? ""] = d = new Dictionary<string, bool>();
                return d;
            }
        }
        readonly CheckBox allFx = new CheckBox { Text = "List every effect of the script", AutoSize = true };
        readonly DataGridView fxGrid = new DataGridView
        {
            Dock = DockStyle.Fill, ReadOnly = true, AllowUserToAddRows = false, AllowUserToDeleteRows = false,
            RowHeadersVisible = false, SelectionMode = DataGridViewSelectionMode.FullRowSelect, MultiSelect = false,
            AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.AllCells,
        };
        bool fxFilling;
        List<FrameState> frames = new List<FrameState>();
        List<FrameState> probe = new List<FrameState>();   // the script run long past the animation
        int animCount = 1;                                   // game frames the animation lasts
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
        readonly CheckBox showFreeze = new CheckBox
        {
            Text = "Show hitlag freeze", AutoSize = true, Checked = Runtime.GetSetting("ViewerShowFreeze", false),
        };
        readonly CheckBox floor = new CheckBox
        {
            Text = "Floor", AutoSize = true, Checked = Runtime.GetSetting("ViewerFloor", true),
        };
        // the slider's frames: {script game frame (1-based), real frame}; with Show hitlag freeze one
        // script frame is shown again for each frame the attacker is frozen
        List<int[]> timeline = new List<int[]>();
        readonly CheckBox untilActionable = new CheckBox
        {
            Text = "Play until the enemy can act", AutoSize = true,
            Checked = Runtime.GetSetting("ViewerUntilActionable", false),
        };
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
            stale = Num(0, 9, 0), kbMult = Num(0, 10, 1, 2), launchRate = Num(0, 10, 1, 2), diAngle = Num(0, 359, 0),
            hitstunMul = Num(0, 20, 1, 2), selfStopMul = Num(0, 20, 1, 2), enemyStopMul = Num(0, 20, 1, 2), diMul = Num(0, 10, 1, 2);
        readonly CheckBox crouch = new CheckBox { Text = "Crouching", AutoSize = true };
        readonly CheckBox aerial = new CheckBox { Text = "Target in the air", AutoSize = true };
        readonly CheckBox useDI = new CheckBox { Text = "DI at", AutoSize = true };
        readonly TextBox results = new TextBox { Multiline = true, ReadOnly = true, Dock = DockStyle.Fill, ScrollBars = ScrollBars.Vertical, Font = new Font(FontFamily.GenericMonospace, 8.5f) };

        static NumericUpDown Num(decimal min, decimal max, decimal val, int dec = 1)
        {
            return new NumericUpDown { Minimum = min, Maximum = max, Value = val, DecimalPlaces = dec, Width = 70, Increment = dec > 1 ? 0.05m : 1 };
        }

        public HitboxViewer(FighterAssets assets, ITS_EDITOR editor, uint scriptCrc, string title, Func<uint, IList<ICommand>> getScript)
            : this(assets, editor, scriptCrc, title, getScript, null, null) { }

        public HitboxViewer(FighterAssets assets, ITS_EDITOR editor, uint scriptCrc, string title, Func<uint, IList<ICommand>> getScript,
                            Func<uint, IList<ICommand>> getEffect, ITS_EDITOR effectEditor)
        {
            this.assets = assets;
            this.getScript = getScript;
            this.getEffect = getEffect;
            library = new EffectLibrary(assets.Root) { CommonName = CommonEffectName };
            // v1.6.1: the common effects' bank: the folder picked before (Common effects..), else the game's
            // data/effect/common found above the fighter's folder
            library.CommonFolder = EffectLibrary.CommonFolderIn(Runtime.GetSettingText("ViewerCommonEffects", "")) ??
                                   EffectLibrary.FindCommonFolder(assets.Root);
            view.EffectLabel = EffectLabel;
            view.GetEffectAssets = library.AssetsFor;
            view.GetTrailTexture = library.TrailTexture;
            Size = new Size(1150, 720);
            StartPosition = FormStartPosition.CenterParent;
            view.Assets = assets;
            Build();
            foreach (var f in FighterAttributes.Load()) target.Items.Add(f);
            target.SelectedIndex = Math.Max(0, target.Items.Cast<FighterAttributes>().ToList().FindIndex(x => x.Name == "Mario"));
            animBox.Items.Add("(none)");
            foreach (var n in assets.AnimationNames) animBox.Items.Add(n);
            animBox.SelectedIndexChanged += (o, e) =>
            {
                if (picking) return;
                animName = animBox.SelectedIndex <= 0 ? null : (string)animBox.SelectedItem;
                currentCrc = ScriptFor(animName);
                Rerun();
            };
            LoadEnemy(Runtime.GetSettingText("ViewerEnemyFolder", ""), false);
            timer.Tick += (o, e) => { bar.Value = bar.Value >= bar.Maximum ? bar.Minimum : bar.Value + 1; };
            editTimer.Tick += (o, e) => { editTimer.Stop(); Rerun(); };
            FormClosed += (o, e) =>
            {
                timer.Stop();
                if (this.editor != null) this.editor.TextChanged -= Editor_TextChanged;
                if (this.effectEditor != null) this.effectEditor.TextChanged -= Editor_TextChanged;
            };
            ShowScript(scriptCrc, editor, title, effectEditor);
        }

        bool picking;           // ShowScript is setting the animation list

        /// <summary>The game script this viewer is for (and the editor whose edits it follows): the
        /// main window calls this again when another script's tab is picked. Shows the script's own
        /// animation; with none known, the animation list says (none).</summary>
        public void ShowScript(uint crc, ITS_EDITOR scriptEditor, string title) { ShowScript(crc, scriptEditor, title, null); }

        /// <summary>v1.5.0: with the tab's effect editor, whose edits the effects follow.</summary>
        public void ShowScript(uint crc, ITS_EDITOR scriptEditor, string title, ITS_EDITOR fxEditor)
        {
            if (editor != null) editor.TextChanged -= Editor_TextChanged;
            editor = scriptEditor;
            if (editor != null) editor.TextChanged += Editor_TextChanged;
            if (effectEditor != null) effectEditor.TextChanged -= Editor_TextChanged;
            effectEditor = fxEditor;
            if (effectEditor != null) effectEditor.TextChanged += Editor_TextChanged;
            scriptCrc = crc;
            currentCrc = crc;
            Text = "Hitbox Viewer - " + title;
            animName = assets.AnimationFor(crc);
            picking = true;
            animBox.SelectedIndex = animName != null ? Math.Max(0, animBox.Items.IndexOf(animName)) : 0;
            picking = false;
            Rerun();
        }

        /// <summary>The game script shown when it was opened for the script being edited (not one
        /// picked through another animation).</summary>
        public uint ScriptCrc { get { return scriptCrc; } }
        public ITS_EDITOR Editor { get { return editor; } }
        /// <summary>v1.6.1: the effect editor whose edits the effects follow (the open tab's), or null.</summary>
        public ITS_EDITOR EffectEditorShown { get { return effectEditor; } }
        /// <summary>v1.6.1: the shown script's game / effect commands as the viewer runs them (tests).</summary>
        public IList<ICommand> ShownGameCommands(out string error) { return CurrentCommands(out error); }
        public IList<ICommand> ShownEffectCommands(out string error) { return EffectCommands(out error); }
        public uint ShownCrc { get { return currentCrc; } }
        public void PickAnimation(string anim)
        {
            int i = animBox.Items.IndexOf(anim);
            animBox.SelectedIndex = i >= 0 ? i : 0;
        }
        public EffectLibrary Library { get { return library; } }
        public FighterAssets Assets { get { return assets; } }

        void Editor_TextChanged(object sender, EventArgs e) { editTimer.Stop(); editTimer.Start(); }

        /// <summary>The game script that plays an animation: the open script if it does, else the
        /// first script named for it that game.bin has, else none (0).</summary>
        uint ScriptFor(string anim)
        {
            if (anim == null) return scriptCrc;
            var list = assets.ScriptsFor(anim);
            if (list.Contains(scriptCrc) || anim == assets.AnimationFor(scriptCrc)) return scriptCrc;
            foreach (var crc in list)
                if (getScript(crc) != null || (getEffect != null && getEffect(crc) != null)) return crc;
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

        /// <summary>v1.6.1: the folder with the common effects (the game's data/effect/common: common.010d0000.efc / .ptcl /
        /// model / trail), remembered in Sm4shCommand.ini.</summary>
        void PickCommonEffects()
        {
            using (var dlg = new FolderBrowserDialog { Description = "The common effects folder: the game's data\\effect\\common (common.010d0000.efc and .ptcl), or a folder above it" })
            {
                if (library.CommonFolder != null) dlg.SelectedPath = library.CommonFolder;
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                string dir = EffectLibrary.CommonFolderIn(dlg.SelectedPath);
                if (dir == null)
                {
                    MessageBox.Show(this, "No common.010d0000.efc there (or in its effect\\common).", "Common effects", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return;
                }
                Runtime.SetSettingText("ViewerCommonEffects", dir);
                library.CommonFolder = dir;
                Rerun();
            }
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
            tools.Height = 84;
            tools.Controls.AddRange(new Control[] { new Label { Text = "Animation:", AutoSize = true, Padding = new Padding(0, 6, 0, 0) }, animBox,
                ifTrue, frameSpeed, showModel, showTextures, showBones, showAngles, showEnemy, untilActionable, showFreeze, floor,
                showHitboxes, showParticles, fxQuality, darkBg, showEffects, showLabels, showTrails, showOverlays, flip });
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
            bar.ValueChanged += (o, e) => { if (!resizing) ShowFrame(); };

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
            row("Launch rate", launchRate, "Hitstun x", hitstunMul);
            row("Attacker hitstop x", selfStopMul, "Enemy hitstop x", enemyStopMul);
            var flags = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            flags.Controls.AddRange(new Control[] { crouch, aerial, useDI, diAngle, new Label { Text = "deg", AutoSize = true, Padding = new Padding(0, 5, 0, 0) },
                new Label { Text = "DI x", AutoSize = true, Padding = new Padding(8, 5, 0, 0) }, diMul });
            calc.Controls.Add(flags);
            calc.SetColumnSpan(flags, 4);
            var tips = new ToolTip();
            tips.SetToolTip(diMul, "DI multiplier: how far DI can turn the launch angle (1 = normal, 0.5 = half, 2 = double, 0 = no DI). " +
                "Multiplies the hitbox's own DIMul (Extra hitboxes).");
            tips.SetToolTip(showParticles, "Draw the effects: the .ptcl particles (simulated from each effect's start), the effect models " +
                "(animated) and the sword trails' textures. Approximate: no game shaders, bloom or distortion (README).");
            tips.SetToolTip(fxQuality, "Higher effect quality: smooth (bilinear) textures and more particles (slower).");
            tips.SetToolTip(darkBg, "A dark background: additive effects show as they do on a stage.");
            tips.SetToolTip(showEffects, "Level 1's effect markers: a circle with the effect's axes at its bone + offset (dashed: one-shot).");
            foreach (Control c in new Control[] { target, targetPct, attackerPct, charge, stale, kbMult, launchRate, diAngle, crouch, aerial, useDI,
                                                  hitstunMul, selfStopMul, enemyStopMul, diMul })
            {
                if (c is NumericUpDown) ((NumericUpDown)c).ValueChanged += (o, e) => Calc();
                else if (c is CheckBox) ((CheckBox)c).CheckedChanged += (o, e) => Calc();
                else if (c is ComboBox) ((ComboBox)c).SelectedIndexChanged += (o, e) => Calc();
            }
            var right = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 200 };
            var tabs = new TabControl { Dock = DockStyle.Fill };
            tabsRight = tabs;
            var hbTab = new TabPage("Hitboxes");
            hbTab.Controls.Add(grid);
            var fxTab = new TabPage("Effects");
            fxTab.Controls.Add(fxGrid);
            fxTab.Controls.Add(allFx);
            allFx.Dock = DockStyle.Bottom;
            tabs.TabPages.Add(hbTab);
            tabs.TabPages.Add(fxTab);
            partsTab = new TabPage("Model parts");
            BuildParts(partsTab);
            tabs.TabPages.Add(partsTab);
            right.Panel1.Controls.Add(tabs);
            fxGrid.SelectionChanged += (o, e) =>
            {
                if (fxFilling) return;
                view.SelectedEffect = fxGrid.SelectedRows.Count > 0 && fxGrid.SelectedRows[0].Tag is EffectData
                    ? ((EffectData)fxGrid.SelectedRows[0].Tag).Index : -1;
                view.Invalidate();
            };
            allFx.CheckedChanged += (o, e) => ShowFrame();
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
            showEffects.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerEffects", showEffects.Checked); view.ShowEffects = showEffects.Checked; view.Invalidate(); };
            showLabels.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerEffectLabels", showLabels.Checked); view.ShowEffectLabels = showLabels.Checked; view.Invalidate(); };
            showTrails.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerTrails", showTrails.Checked); view.ShowTrails = showTrails.Checked; view.Invalidate(); };
            flip.CheckedChanged += (o, e) => { view.Flip = flip.Checked; ShowFrame(); };
            showParticles.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerParticles", showParticles.Checked); view.ShowParticles = showParticles.Checked; view.Invalidate(); };
            fxQuality.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerFxQuality", fxQuality.Checked); view.HighQuality = fxQuality.Checked; view.ResetEffects(); };
            darkBg.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerDarkBg", darkBg.Checked); view.DarkBackground = darkBg.Checked; view.Invalidate(); };
            showHitboxes.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerHitboxes", showHitboxes.Checked); view.ShowHitboxes = showHitboxes.Checked; view.Invalidate(); };
            showOverlays.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerOverlays", showOverlays.Checked); view.ShowOverlays = showOverlays.Checked; view.Invalidate(); };
            view.ShowHitboxes = showHitboxes.Checked;
            view.ShowOverlays = showOverlays.Checked;
            view.ShowParticles = showParticles.Checked;
            view.HighQuality = fxQuality.Checked;
            view.DarkBackground = darkBg.Checked;
            view.ShowEffects = showEffects.Checked;
            view.ShowEffectLabels = showLabels.Checked;
            view.ShowTrails = showTrails.Checked;
            untilActionable.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerUntilActionable", untilActionable.Checked); Calc(); };
            showFreeze.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerShowFreeze", showFreeze.Checked); Calc(); };
            floor.CheckedChanged += (o, e) => { Runtime.SetSetting("ViewerFloor", floor.Checked); Calc(); };
            var meshes = new Button { Text = "Model parts..", AutoSize = true };
            meshes.Click += (o, e) => PickMeshes();
            var enemyButton = new Button { Text = "Enemy model..", AutoSize = true };
            enemyButton.Click += (o, e) => PickEnemy();
            var commonButton = new Button { Text = "Common effects..", AutoSize = true };
            commonButton.Click += (o, e) => PickCommonEffects();
            tools.Controls.Add(meshes);
            tools.Controls.Add(enemyButton);
            tools.Controls.Add(commonButton);
        }

        /// <summary>Meshes..: the Model parts tab (v1.6.2; it replaces the old mesh dialog).</summary>
        void PickMeshes() { tabsRight.SelectedTab = partsTab; }

        /// <summary>v1.6.2: the Model parts tab: every mesh of the model (and of the held model) with a box to show / hide
        /// it, what the frame would show without your choice and why; Reset to script / default, Show all, Hide all.</summary>
        void BuildParts(TabPage page)
        {
            partsGrid.Columns.Add(new DataGridViewCheckBoxColumn { Name = "Show", HeaderText = "Show", Width = 44 });
            foreach (var c in new[] { "Mesh", "Now", "Why" })
                partsGrid.Columns.Add(new DataGridViewTextBoxColumn { Name = c, HeaderText = c, ReadOnly = true });
            partsGrid.CurrentCellDirtyStateChanged += (o, e) => { if (partsGrid.IsCurrentCellDirty) partsGrid.CommitEdit(DataGridViewDataErrorContexts.Commit); };
            partsGrid.CellValueChanged += (o, e) =>
            {
                if (partsFilling || e.RowIndex < 0 || e.ColumnIndex != 0) return;
                var row = partsGrid.Rows[e.RowIndex];
                string mesh = (string)row.Tag;
                if (mesh == null) return;
                UserParts[mesh] = (bool)row.Cells[0].Value;
                ShowFrame();
            };
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 32 };
            var reset = new Button { Text = "Reset to script / default", AutoSize = true };
            reset.Click += (o, e) => { UserParts.Clear(); ShowFrame(); };
            var all = new Button { Text = "Show all", AutoSize = true };
            all.Click += (o, e) => { foreach (var m in AllMeshes()) UserParts[m] = true; ShowFrame(); };
            var none = new Button { Text = "Hide all", AutoSize = true };
            none.Click += (o, e) => { foreach (var m in AllMeshes()) UserParts[m] = false; ShowFrame(); };
            buttons.Controls.AddRange(new Control[] { reset, all, none });
            // v1.6.3: the right-click menu (the selected rows, or the one clicked)
            var menu = new ContextMenuStrip();
            Func<List<string>> picked = () => partsGrid.SelectedRows.Cast<DataGridViewRow>().Select(r => (string)r.Tag).Where(t => t != null).ToList();
            Action<string, Action<List<string>>> item = (text, act) =>
                menu.Items.Add(text, null, (o, e) => { var l = picked(); if (l.Count > 0) { act(l); ShowFrame(); } });
            item("Show now", l => PartsMenu.Now(UserParts, l, true));
            item("Hide now", l => PartsMenu.Now(UserParts, l, false));
            menu.Items.Add(new ToolStripSeparator());
            item("Hidden by default for this fighter", l => PartsWarn(PartsMenu.Default(visGroups, UserParts, assets.Name, l, false)));
            item("Visible by default", l => PartsWarn(PartsMenu.Default(visGroups, UserParts, assets.Name, l, true)));
            item("Follow the script / default", l => PartsWarn(PartsMenu.Default(visGroups, UserParts, assets.Name, l, null)));
            menu.Items.Add(new ToolStripSeparator());
            item("Isolate", l => PartsMenu.Isolate(UserParts, AllMeshes(), l));
            menu.Items.Add("Show all", null, (o, e) => { PartsMenu.Isolate(UserParts, AllMeshes(), AllMeshes().ToList()); ShowFrame(); });
            partsGrid.ContextMenuStrip = menu;
            partsGrid.CellMouseDown += (o, e) =>
            {
                // a right click on a row outside the selection picks that row
                if (e.Button != MouseButtons.Right || e.RowIndex < 0) return;
                if (!partsGrid.Rows[e.RowIndex].Selected) { partsGrid.ClearSelection(); partsGrid.Rows[e.RowIndex].Selected = true; }
            };
            page.Controls.Add(partsGrid);
            page.Controls.Add(partsInfo);
            page.Controls.Add(buttons);
        }

        void PartsWarn(bool saved)
        {
            if (!saved) MessageBox.Show(this, "Couldn't write " + (visGroups.UserPath ?? "VisUser.txt") +
                                        ": the choice holds until the program closes.", "Model parts");
        }

        IEnumerable<string> AllMeshes()
        {
            foreach (var m in assets.Model.Meshes) yield return m.Name;
            if (view.Held != null) foreach (var m in view.Held.Model.Meshes) yield return "held: " + m.Name;
        }

        /// <summary>The meshes shown on this frame (ModelParts.Apply) and the parts tab's rows.</summary>
        void ApplyParts(FrameState f, float af)
        {
            var vis = f != null ? f.Vis : null;
            ModelParts.Apply(assets, animName, af, vis, visGroups, UserParts);
            view.WholeVisible = vis == null || !vis.Whole.HasValue || vis.Whole.Value;
            if (view.Held != null)
                foreach (var m in view.Held.Model.Meshes)
                {
                    bool v;
                    if (UserParts.TryGetValue("held: " + m.Name, out v)) { m.Visible = v; m.Why = "your choice"; }
                    else { m.Visible = m.DefaultVisible; m.Why = "held model (" + view.Held.Name + ")"; }
                }
            view.Invalidate();
            if (partsTab == null) return;
            partsFilling = true;
            partsGrid.SuspendLayout();
            var rows = new List<Tuple<string, bool, string>>();
            foreach (var m in assets.Model.Meshes) rows.Add(Tuple.Create(m.Name, m.Visible, m.Why));
            if (view.Held != null) foreach (var m in view.Held.Model.Meshes) rows.Add(Tuple.Create("held: " + m.Name, m.Visible, m.Why));
            if (partsGrid.Rows.Count != rows.Count) { partsGrid.Rows.Clear(); foreach (var r in rows) partsGrid.Rows.Add(false, "", "", ""); }
            for (int i = 0; i < rows.Count; i++)
            {
                var row = partsGrid.Rows[i];
                row.Tag = rows[i].Item1;
                row.Cells[0].Value = rows[i].Item2;
                row.Cells[1].Value = rows[i].Item1;
                row.Cells[2].Value = rows[i].Item2 ? "shown" : "hidden";
                row.Cells[3].Value = rows[i].Item3 + (UserParts.ContainsKey(rows[i].Item1) ? "" : "");
                row.DefaultCellStyle.ForeColor = rows[i].Item2 ? SystemColors.ControlText : SystemColors.GrayText;
            }
            partsGrid.ResumeLayout();
            partsFilling = false;
            var ev = vis != null ? vis.Events.Where(x => x.Frame <= f.GameFrame).Select(x => x.Frame + ": " + x.Text.Split('(')[0] + "(" + x.Text.Split('(').Skip(1).FirstOrDefault()).ToList() : new List<string>();
            partsInfo.Text = (ev.Count > 0 ? "Script visibility so far: " + string.Join("; ", ev.ToArray()) : "No visibility commands so far in this script.") +
                             (vis != null && vis.Groups.Count > 0 ? "  Groups now: " + string.Join(", ", vis.Groups.Select(kv => kv.Key + "=" + kv.Value).ToArray()) +
                              (visGroups.Fighters.ContainsKey(assets.Name) ? "" : " (VisGroups.txt has no groups for " + assets.Name + ": not applied to meshes)") : "") +
                             (assets.MaterialVis != null && assets.MaterialVis.Files > 0 ? "  Visibility animations: " + assets.MaterialVis.Files + " motion files." : "");
        }

        /// <summary>The game script for the shown script (ScriptCommands: the open tab's game editor, else game.bin's).</summary>
        IList<ICommand> CurrentCommands(out string error) { return ScriptCommands(getScript, editor, out error); }

        /// <summary>
        /// v1.6.1: one rule for the game script (hitboxes) and the effect script (effects): the shown script is the open
        /// tab's while its animation is shown (the editor's text, compiled as you type; a compile error falls back to the
        /// saved script and says why), else the saved file's script of the animation picked here (getScript / getEffect:
        /// the open file in the main window, else the file on disk next to it).
        /// </summary>
        IList<ICommand> ScriptCommands(Func<uint, IList<ICommand>> saved, ITS_EDITOR open, out string error)
        {
            return PickCommands(currentCrc, scriptCrc, saved, open != null ? (Func<IList<string>>)(() => open.Lines) : null, out error);
        }

        /// <summary>The rule itself (static, for tests): shown = the animation shown, tab = the open tab's script, lines =
        /// the tab's editor text for this kind (null: no editor).</summary>
        public static IList<ICommand> PickCommands(uint shown, uint tab, Func<uint, IList<ICommand>> saved, Func<IList<string>> lines, out string error)
        {
            error = null;
            if (shown == 0) return null;
            if (shown == tab && lines != null)
            {
                // a preview compile while typing: New_Var names typed half-way (c, ch, cha, ...) mustn't take slots
                var names = SALT.Moveset.FighterVariable.SaveNewVars();
                try
                {
                    var stripped = ACMDCompiler.StripComments(lines().ToArray());
                    return ACMDCompiler.CompileCommands(stripped.ToArray()).Cast<ICommand>().ToList();
                }
                catch (Exception ex) { error = ex.Message.Split('\n')[0]; }
                finally { SALT.Moveset.FighterVariable.RestoreNewVars(names); }
            }
            return saved != null ? saved(shown) : null;
        }

        void Rerun()
        {
            view.MarkerOnlyHint = library.CommonFolder == null ? "; common effects: Common effects.. picks data\\effect\\common" : "";
            string error;
            var cmds = CurrentCommands(out error);
            anim = assets.GetAnimation(animName);
            int length = anim != null ? anim.Frames : 0;
            var runner = new HitboxRunner { ConditionsTrue = ifTrue.Checked, UseFrameSpeed = frameSpeed.Checked, GetScript = getScript };
            // enough game frames for the whole animation (slowed down by Set_Frame_Duration), or 120
            probe = runner.Run(cmds ?? new List<ICommand>(), 600);
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
            animCount = Math.Max(1, n);
            RunEffects();
            RunExpression();
            frames = probe.Take(animCount).ToList();
            view.History = probe;
            view.ResetEffects();
            SetTimeline(animCount, null, 0);
            view.Animation = anim;
            var hm = assets.HeldFor(animName);
            view.Held = hm != null ? hm.Item1 : null;
            view.HeldBone = hm != null ? hm.Item2 : -1;
            Text = "Hitbox Viewer - " + (currentCrc == 0 ? "(no script)" : Runtime.ScriptLabel(currentCrc)) +
                   (currentCrc != scriptCrc && currentCrc != 0 ? " (saved game.bin; edits follow the open script only)" : "");
            status.Text = (error != null ? "Doesn't compile (showing the last saved script): " + error + "   " : "") +
                          (effectError != null ? "Effect script doesn't compile (showing the saved one): " + effectError + "   " : "") +
                          (animName != null ? animName + ", " + length + " frames" : "No animation found for this script: pick one above") +
                          (cmds == null ? "   (no game script for this animation: no hitboxes)" : "");
            ShowFrame();
        }

        void ShowFrame()
        {
            if (frames.Count == 0 || timeline.Count == 0) return;
            var f = frames[ScriptIndex()];
            view.Frame = f;
            float af = Math.Max(0, f.AnimFrame);
            if (anim != null && anim.Frames > 0) af = Math.Min(af, anim.Frames - 1);   // holds its last frame after the end
            view.AnimFrame = af;
            view.TrailFrames = new List<float>();
            for (int i = ScriptIndex() - 1; i >= 0 && view.TrailFrames.Count < 16; i--)
                view.TrailFrames.Add(Math.Max(0, frames[i].AnimFrame));
            FillEffects(f);
            ApplyParts(f, af);
            UpdateLabel(f, af);
            int sel = view.SelectedHitbox;
            filling = true;
            grid.SuspendLayout();
            grid.Rows.Clear();
            if (grid.Columns.Count == 0)
                foreach (var c in new[] { "ID", "Damage", "Angle", "KBG", "WBKB", "BKB", "Size", "Bone", "Hitlag", "SDI", "Effect", "Extras", "Command" })
                    grid.Columns.Add(c, c);
            foreach (var h in f.Hitboxes)
            {
                int r = grid.Rows.Add(h.Id, h.Damage, h.Angle, h.KBG, h.WBKB, h.BKB, h.Size, "0x" + h.Bone.ToString("X"), h.Hitlag, h.SDI, h.Effect, h.ExtrasText, h.Command);
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

        // ---- effects (v1.5.0) -----------------------------------------------------------------------------------------

        /// <summary>The effect script for the shown script: the same rule as the game script's (ScriptCommands).</summary>
        IList<ICommand> EffectCommands(out string error) { return ScriptCommands(getEffect, effectEditor, out error); }

        /// <summary>Runs the effect script on the game script's timeline (its per-frame speeds) and puts its effects,
        /// trails and screen events on the probe's frames.</summary>
        /// <summary>v1.6.2: the expression script on the same timeline (the same rule as the game / effect scripts): its
        /// visibility commands (Model_Changer & co.) and overlays join the frames'.</summary>
        void RunExpression()
        {
            string err;
            var cmds = ScriptCommands(getExpression, expressionEditor, out err);
            if (cmds == null || probe.Count == 0) return;
            var r = new HitboxRunner { ConditionsTrue = ifTrue.Checked, GetScript = getExpression, SpeedSchedule = probe.Select(x => x.Speed).ToArray() };
            var ex = r.Run(cmds, probe.Count);
            for (int i = 0; i < probe.Count && i < ex.Count; i++)
            {
                if (probe[i].Overlay == null && ex[i].Overlay != null) { probe[i].Overlay = ex[i].Overlay; probe[i].OverlayLight = ex[i].OverlayLight; }
                probe[i].Vis = VisState.Merge(ex[i].Vis, probe[i].Vis);
            }
        }

        /// <summary>v1.6.2: the expression scripts (expression.bin's, and the open tab's expression editor while it shows).</summary>
        public void SetExpression(Func<uint, IList<ICommand>> saved, ITS_EDITOR open)
        {
            if (expressionEditor != null) expressionEditor.TextChanged -= Editor_TextChanged;
            getExpression = saved;
            expressionEditor = open;
            if (expressionEditor != null) expressionEditor.TextChanged += Editor_TextChanged;
            // v1.6.3: run again with it (set after the viewer was made, its visibility commands waited for an edit)
            if (probe != null) Rerun();
        }

        void RunEffects()
        {
            var cmds = EffectCommands(out effectError);
            allEffects = new List<EffectData>();
            allTrails = new List<TrailData>();
            if (cmds == null || probe.Count == 0) return;
            var r = new HitboxRunner
            {
                ConditionsTrue = ifTrue.Checked, GetScript = getEffect, SpeedSchedule = probe.Select(x => x.Speed).ToArray(),
                OneShotLife = LifeOf,
            };
            var fx = r.Run(cmds, probe.Count);
            for (int i = 0; i < probe.Count && i < fx.Count; i++)
            {
                probe[i].Effects = fx[i].Effects;
                probe[i].Trails = fx[i].Trails;
                probe[i].Screen = fx[i].Screen;
                // v1.6.2: an overlay / visibility command in the effect script too
                if (fx[i].Overlay != null) { probe[i].Overlay = fx[i].Overlay; probe[i].OverlayLight = fx[i].OverlayLight; }
                probe[i].Vis = VisState.Merge(probe[i].Vis, fx[i].Vis);
            }
            allEffects = r.AllEffects;
            allTrails = r.AllTrails;
        }

        int LifeOf(uint id)
        {
            if (id == 0) return 0;
            var l = library.Lifetime(id);
            return l.HasValue ? Math.Max(1, l.Value) : (library.GetBank((int)(id >> 16)) != null ? -1 : 0);
        }

        static string CommonEffectName(uint id)
        {
            var e = Sm4shCommand.Classes.Tooltips.Find(id, "Graphic_Effect", "Graphic", "int").FirstOrDefault();
            return e != null ? e.Name : null;
        }

        string NameOf(EffectData e)
        {
            uint id = e.IdFor(flip.Checked);
            if (id == 0) return e.WorkVar != 0 ? "(from variable 0x" + e.WorkVar.ToString("X") + ")" : "";
            return library.Name(id);
        }

        string EffectLabel(EffectData e)
        {
            uint id = e.IdFor(flip.Checked);
            string name = NameOf(e);
            return (id != 0 ? "0x" + id.ToString("X") : "?") + (name.Length > 0 ? " " + name : "");
        }

        void FillEffects(FrameState f)
        {
            var ic = CultureInfo.InvariantCulture;
            int sel = view.SelectedEffect;
            fxFilling = true;
            fxGrid.SuspendLayout();
            fxGrid.Rows.Clear();
            if (fxGrid.Columns.Count == 0)
                foreach (var c in new[] { "#", "ID", "Name", "Bone", "Offset", "Rotation", "Size", "Colour / alpha", "Kind",
                                          "Frames", "Facing left", "Command" })
                    fxGrid.Columns.Add(c, c);
            var list = allFx.Checked ? allEffects : f.Effects ?? new List<EffectData>();
            foreach (var e in list)
            {
                uint id = e.IdFor(flip.Checked);
                string kind = e.Follow ? (e.DetachFrame >= 0 ? "follow, detached " + e.DetachFrame : "follow") : "one-shot";
                if (e.World) kind += ", world";
                string frames = e.StartFrame + "-" + (e.EndFrame >= 0 ? (e.EndFrame - 1).ToString() : "end") +
                                (e.EndReason.Length > 0 ? " (" + e.EndReason + ")" : "");
                string col = (e.HasColor ? string.Format(ic, "{0:0.###} {1:0.###} {2:0.###}", e.R, e.G, e.B) : "-") +
                             (e.HasAlpha ? string.Format(ic, " a {0:0.###}", e.A) : "") + (e.Rate != 1 ? string.Format(ic, " rate {0:0.###}", e.Rate) : "") +
                             (e.HasScale ? string.Format(ic, " scale {0:0.##} {1:0.##} {2:0.##}", e.SX, e.SY, e.SZ) : "");
                string facing = FacingRule.Check(e);
                if (e.HasLeft) facing = (facing.Length > 0 ? facing + "; " : "") + "left: 0x" + e.IdLeft.ToString("X");
                int row = fxGrid.Rows.Add(e.Index, id != 0 ? "0x" + id.ToString("X") : "?", NameOf(e),
                    e.World ? "-" : e.Bone < 0 ? "(by name)" : "0x" + e.Bone.ToString("X"),
                    string.Format(ic, "{0:0.##}, {1:0.##}, {2:0.##}", e.X, e.Y, e.Z),
                    string.Format(ic, "{0:0.##}, {1:0.##}, {2:0.##}", e.RX, e.RY, e.RZ),
                    e.Size.ToString("0.###", ic), col, kind, frames, facing.Length > 0 ? "! " + facing : "ok", e.Command);
                fxGrid.Rows[row].Tag = e;
                var c0 = Viewport.EffectColor(e);
                fxGrid.Rows[row].DefaultCellStyle.BackColor = Color.FromArgb(255 - (255 - c0.R) * 2 / 10, 255 - (255 - c0.G) * 2 / 10, 255 - (255 - c0.B) * 2 / 10);
                if (sel == e.Index) fxGrid.Rows[row].Selected = true;
            }
            foreach (var t in (allFx.Checked ? allTrails : f.Trails ?? new List<TrailData>()))
                fxGrid.Rows.Add("trail " + t.Index, t.Graphic != 0 ? "0x" + t.Graphic.ToString("X") : "", "sword trail",
                    "0x" + t.Bone1.ToString("X") + " / 0x" + t.Bone2.ToString("X"),
                    string.Format(ic, "{0:0.##}, {1:0.##}, {2:0.##} / {3:0.##}, {4:0.##}, {5:0.##}", t.X1, t.Y1, t.Z1, t.X2, t.Y2, t.Z2),
                    "", "", "", "trail (blur " + t.Blur + ")",
                    t.StartFrame + "-" + (t.EndFrame >= 0 ? (t.EndFrame - 1).ToString() : "end") + (t.Fade > 0 ? " + fade " + t.Fade : ""), "", t.Command);
            foreach (var ev in f.Screen ?? new List<ScreenEvent>())
                fxGrid.Rows.Add("screen", "", "", "", "", "", "", "", "listed only", ev.Frame.ToString(), "", ev.Text);
            fxGrid.ClearSelection();
            foreach (DataGridViewRow r in fxGrid.Rows)
                if (r.Tag is EffectData && ((EffectData)r.Tag).Index == sel) r.Selected = true;
            fxGrid.ResumeLayout();
            fxFilling = false;
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
            int cur = frames.Count > 0 && timeline.Count > 0 ? ScriptIndex() : -1;
            int real = timeline.Count > 0 ? timeline[Pos()][1] : 0;
            int hitFrame = -1;
            var hb = cur < 0 ? null : PickedHitbox(cur, out hitFrame);
            if (hb == null)
            {
                results.Text = cur < 0 || frames[cur].Hitboxes.Count == 0 ? "No hitboxes on this frame." : "Pick a hitbox in the list.";
                view.Trajectory = null;
                view.TrajectoryOrigin = null;
                if (SetTimeline(animCount, null, 0)) return;
                PlaceEnemy(null, 0, real, null);
                view.Recompute();
                return;
            }
            var inp = new KnockbackInput
            {
                Hitbox = hb, Target = target.SelectedItem as FighterAttributes, TargetPercent = (float)targetPct.Value,
                AttackerPercent = (float)attackerPct.Value, StaleCount = (int)stale.Value, ChargeFrames = (float)charge.Value,
                Crouching = crouch.Checked, TargetAerial = aerial.Checked, KbMultiplier = (float)kbMult.Value,
                LaunchRate = (float)launchRate.Value, UseDI = useDI.Checked, DIAngle = (float)diAngle.Value,
                DIMultiplier = (float)diMul.Value,
            };
            var r = KnockbackCalc.Calculate(inp);
            // the viewer's own multipliers, before the script's changes
            double hm = (double)hitstunMul.Value, am = (double)selfStopMul.Value, em = (double)enemyStopMul.Value;
            if (hm != 1 || am != 1 || em != 1)
            {
                r.Hitstun = r.FinalHitstun = (int)Math.Round(r.Hitstun * hm);
                r.AttackerHitlag = r.FinalAttackerHitlag = (int)Math.Round(r.AttackerHitlag * am);
                r.TargetHitlag = r.FinalTargetHitlag = (int)Math.Round(r.TargetHitlag * em);
                KnockbackCalc.Retime(r);
                r.AirdodgeCancel = r.FinalAirdodgeCancel;
                r.AerialCancel = r.FinalAerialCancel;
            }
            ScriptModifiers.Apply(r, hitFrame, probe.Take(Math.Max(frames.Count, animCount)).SelectMany(f => f.Writes));
            KnockbackCalc.Retime(r);
            var end = r.Path[Math.Min(r.FinalHitstun, r.Path.Count - 1)];
            int frozen = r.TargetStops.Sum(x => x[1]);
            // the game frame (of this script's timeline) the enemy can act on
            int actsReal = hitFrame + r.FinalTargetHitlag + r.FinalHitstun + frozen + 1;
            int stopsBefore = r.AttackerStops.Where(x => x[0] < actsReal).Sum(x => x[1]);
            int actsFrame = actsReal - (actsReal > hitFrame ? stopsBefore : 0);
            // the slider shows script frames, or real frames with the freeze; ShowFrame again when it changes
            if (SetTimeline(untilActionable.Checked ? Math.Max(animCount, actsFrame) : animCount, r, hitFrame)) return;
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
                string.Format(ic, "Hitstun cancel     airdodge {0}, aerial {1}{2}", r.FinalAirdodgeCancel, r.FinalAerialCancel,
                    r.FinalAirdodgeCancel != r.AirdodgeCancel || r.FinalAerialCancel != r.AerialCancel
                        ? string.Format(ic, "  (without the script: {0}, {1})", r.AirdodgeCancel, r.AerialCancel) : ""),
                string.Format(ic, "Hitlag             attacker {0}, target {1}  (hitlag x{2:0.##})", r.FinalAttackerHitlag, r.FinalTargetHitlag, hb.Hitlag),
                string.Format(ic, "Shield             stun {0}, hitlag {1}", r.ShieldStun, r.ShieldHitlag),
                string.Format(ic, "Distance           {0:0.##} forward, {1:0.##} up at the end of hitstun", end[0], end[1]),
                string.Format(ic, "Hits on game frame {0}; the enemy can act on game frame {1} of the script ({2} counting the hitlag freeze)", hitFrame, actsFrame, actsReal),
            };
            if (hb.HasExtras)
                lines.Add(string.Format(ic, "{0} extras     {1}", hb.Command, hb.ExtrasText.Length > 0 ? hb.ExtrasText : "none (all x1 / computed)"));
            float diTotal = (float)diMul.Value * hb.DIMultiplier;
            if (diTotal != 1)
                lines.Add(string.Format(ic, "DI                 x{0:0.###}{1}", diTotal, useDI.Checked ? "" : "  (tick \"DI at\" to use it)"));
            if (r.ScriptNotes.Count > 0)
            {
                lines.Add("");
                lines.Add("The script's modifiers (on top of the multipliers above):");
                lines.AddRange(r.ScriptNotes.Select(x => "  " + x));
                if (changed)
                    lines.Add(string.Format(ic, "  Without them: hitstun {0}, hitlag attacker {1}, target {2}", r.Hitstun, r.AttackerHitlag, r.TargetHitlag));
            }
            lines.Add("");
            lines.Add("Formulas: Sm4sh-Calculator (rubendal). Trajectory: no stage, dashed in the view.");
            results.Text = string.Join("\r\n", lines.ToArray());
            view.Trajectory = r.Path;
            real = timeline[Pos()][1];
            PlaceEnemy(hb, hitFrame, real, r);
            view.Recompute();
        }

        bool resizing;

        int Pos() { return Math.Max(0, Math.Min(bar.Value, timeline.Count) - 1); }
        int ScriptIndex() { return Math.Max(0, Math.Min(timeline[Pos()][0], frames.Count) - 1); }
        bool Frozen() { int i = Pos(); return i > 0 && timeline[i - 1][0] == timeline[i][0]; }

        void UpdateLabel(FrameState f, float af)
        {
            bool real = showFreeze.Checked && timeline.Count != frames.Count;
            frameLabel.Text = string.Format(CultureInfo.InvariantCulture, "frame {0} / {1}{2}   anim {3:0.##}{4}{5}", bar.Value, timeline.Count,
                real ? " (script " + f.GameFrame + ")" : "", af + 1,
                Frozen() ? " (hitlag freeze)" : "", f.GameFrame > animCount ? " (animation over)" : "");
        }

        bool reshowing;

        /// <summary>Shows count script frames: the animation's, or more, to the frame the enemy can act
        /// (the attacker holds its last pose; the script keeps running). Real frames: the attacker
        /// stands still in its hitlag (and SELF_HITSTOP) after the frame it happens on; with Show hitlag
        /// freeze those frames are on the slider too. True when the slider changed and the frame was
        /// shown again (the caller's work is then done).</summary>
        bool SetTimeline(int count, KnockbackResult r, int hitFrame)
        {
            if (probe.Count == 0) return false;
            count = Math.Max(1, Math.Min(count, probe.Count));
            var stops = r != null ? r.AttackerStops : new List<int[]>();
            var t = new List<int[]>();
            int extra = 0;
            for (int sf = 1; sf <= count; sf++)
            {
                t.Add(new[] { sf, sf + extra });
                foreach (var st in stops)
                    if (st[0] == sf && st[1] > 0)
                    {
                        if (showFreeze.Checked)
                            for (int k = 1; k <= st[1]; k++) t.Add(new[] { sf, sf + extra + k });
                        extra += st[1];
                    }
            }
            bool same = t.Count == timeline.Count && frames.Count == count;
            for (int i = 0; same && i < t.Count; i++)
                same = t[i][0] == timeline[i][0] && t[i][1] == timeline[i][1];
            if (same) return false;
            // keep the same script frame under the slider when the freeze frames come and go
            int keepScript = timeline.Count > 0 ? timeline[Pos()][0] : 1;
            bool wasFrozen = timeline.Count > 0 && Frozen();
            int keepReal = timeline.Count > 0 ? timeline[Pos()][1] : 1;
            frames = probe.Take(count).ToList();
            timeline = t;
            int pos = showFreeze.Checked && wasFrozen ? t.FindIndex(x => x[1] == keepReal) : t.FindIndex(x => x[0] == keepScript);
            if (pos < 0) pos = Math.Min(keepScript, t.Count) - 1;
            if (reshowing || resizing) return false;
            resizing = true;
            bar.Maximum = t.Count;
            bar.Value = Math.Max(1, Math.Min(pos + 1, t.Count));
            resizing = false;
            reshowing = true;
            ShowFrame();
            reshowing = false;
            return true;
        }

        /// <summary>Puts the enemy where the hitbox hits it (on the ground, or at the hitbox's height
        /// in the air), standing until the hit, then in hitlag, then along the trajectory with its
        /// damage animation. Real time: the attacker's script waits out its hitlag.</summary>
        void PlaceEnemy(HitboxData hb, int hitFrame, int frame, KnockbackResult r)
        {
            view.TrajectoryOrigin = null;
            view.EnemyStatus = null;
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
                int real = frame;
                int launch = hitFrame + r.FinalTargetHitlag;
                var damage = enemy.GetAnimation(r.Tumble ? enemyFly ?? enemyHurt : enemyHurt ?? enemyFly);
                if (damage != null) e.Animation = damage;
                string name = enemy.Name.Length > 0 ? char.ToUpper(enemy.Name[0]) + enemy.Name.Substring(1) : "Enemy";
                if (real < launch)
                {
                    e.Frame = 0;
                    e.Z += (real & 1) == 0 ? 0.35f : -0.35f;     // shaking in hitlag
                    view.EnemyStatus = string.Format("{0}: hitlag, {1} frames left", name, launch - real);
                }
                else
                {
                    int t = real - launch, k = t, stopLeft = 0;
                    foreach (var stop in r.TargetStops)
                        if (t >= stop[0] && t < stop[0] + stop[1]) stopLeft = stop[0] + stop[1] - t;
                    foreach (var stop in r.TargetStops)
                        if (k > stop[0]) k -= Math.Min(stop[1], k - stop[0]);
                    var p = r.Path[Math.Min(k, r.Path.Count - 1)];
                    e.Z += p[0];
                    e.Y = floor.Checked ? Math.Max(0, e.Y + p[1]) : e.Y + p[1];   // Floor off: falls through
                    e.Frame = e.Animation != null ? Math.Min(k, Math.Max(0, e.Animation.Frames - 1)) : 0;
                    int left = r.FinalHitstun - k;
                    if (stopLeft > 0)
                    {
                        e.Z += (t & 1) == 0 ? 0.35f : -0.35f;
                        view.EnemyStatus = string.Format("{0}: hitstop, {1} frames left ({2} frames of hitstun after it)", name, stopLeft, left);
                    }
                    else if (left > 0)
                    {
                        var can = new List<string>();
                        if (t + 1 >= r.FinalAirdodgeCancel) can.Add("airdodge");
                        if (t + 1 >= r.FinalAerialCancel) can.Add("aerial");
                        view.EnemyStatus = string.Format("{0}: hitstun, {1} frames left{2}", name, left,
                            can.Count > 0 ? " (can cancel with " + string.Join(" / ", can.ToArray()) + ")" : "");
                    }
                    else
                    {
                        view.EnemyStatus = name + ": out of hitstun, can act";
                        if (floor.Checked && e.Y <= 0 && enemyStand != null)      // back on the ground: standing again
                        {
                            e.Animation = enemy.GetAnimation(enemyStand);
                            if (e.Animation != null && e.Animation.Frames > 0) e.Frame = (-left) % e.Animation.Frames;
                        }
                    }
                }
            }
            view.Enemy = e;
            view.TrajectoryOrigin = new[] { 0f, y0, z0 };
        }

        /// <summary>The hitbox's world position on game frame (x, y, z).</summary>
        float[] HitboxPosition(HitboxData hb, int gameFrame)
        {
            if (gameFrame < 1 || gameFrame > frames.Count) return null;
            float af = Math.Max(0, frames[gameFrame - 1].AnimFrame);
            if (anim != null && anim.Frames > 0) af = Math.Min(af, anim.Frames - 1);
            var world = assets.Skeleton.World(anim, af);
            int bi = assets.Skeleton.ScriptBone(hb.Bone);
            if (bi < 0 || bi >= world.Length) return null;
            return world[bi].ClearScale().Transform(hb.X, hb.Y, hb.Z);
        }
    }
}
