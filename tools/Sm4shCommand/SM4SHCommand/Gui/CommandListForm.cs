using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using SALT.Moveset.AnimCMD;

namespace Sm4shCommand
{
    /// <summary>
    /// View > Commands: every ACMD command, grouped by what it does (its "Category:" in Events.cfg),
    /// with its description, parameters (type and meaning), a template line and a usage example (its
    /// "Example:" lines). A search box filters by name, identifier, description or parameter. Insert (or
    /// double-click) puts the template in the open script at the caret, Insert Example the example;
    /// Copy / Copy Example put them on the clipboard.
    /// </summary>
    public class CommandListForm : Form
    {
        // groups in this order; any other group after them, alphabetically, and Other last
        static readonly string[] GroupOrder =
        {
            "Script flow & timing", "Variables & compares", "Hitboxes", "Grabs & throws", "Hurtboxes & body",
            "Search boxes, areas & shields", "Effects", "Trails & sword glow", "Lights, flashes & overlays",
            "Sound", "Camera, quake & rumble", "Slowdown", "Movement & physics", "Animation, model & visibility",
            "Articles (projectiles)", "Items", "Item scripts (IT_)", "Traces & targeting", "Fighter-specific",
        };
        static readonly string[] TypeNames = { "int", "float", "decimal", "variable" };

        readonly Func<ITS_EDITOR> activeEditor;
        readonly TextBox search = new TextBox { Dock = DockStyle.Fill };
        readonly TreeView tree = new TreeView { Dock = DockStyle.Fill, HideSelection = false, ShowNodeToolTips = true };
        readonly RichTextBox info = new RichTextBox
        {
            Dock = DockStyle.Fill, ReadOnly = true, BorderStyle = BorderStyle.None, BackColor = SystemColors.Window,
            DetectUrls = false,
        };
        readonly Button btnInsert = new Button { Text = "Insert into Script", AutoSize = true };
        readonly Button btnCopy = new Button { Text = "Copy", AutoSize = true };
        readonly Button btnInsertExample = new Button { Text = "Insert Example", AutoSize = true };
        readonly Button btnCopyExample = new Button { Text = "Copy Example", AutoSize = true };
        readonly Label lblCount = new Label { AutoSize = true, ForeColor = Color.DimGray, Anchor = AnchorStyles.Left, Margin = new Padding(6, 8, 3, 0) };
        readonly Timer searchDelay = new Timer { Interval = 200 };
        uint? current;

        /// <param name="activeEditor">the script editor Insert writes to (null: none open)</param>
        public CommandListForm(Func<ITS_EDITOR> activeEditor)
        {
            this.activeEditor = activeEditor;
            Text = "ACMD Commands";
            Size = new Size(1000, 640);
            StartPosition = FormStartPosition.CenterParent;
            MinimizeBox = false;
            ShowInTaskbar = false;

            var top = new TableLayoutPanel { Dock = DockStyle.Top, ColumnCount = 3, Height = 30, Padding = new Padding(4, 4, 4, 0) };
            top.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            top.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            top.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            top.Controls.Add(new Label { Text = "Search:", AutoSize = true, Anchor = AnchorStyles.Left, Margin = new Padding(0, 6, 3, 0) }, 0, 0);
            top.Controls.Add(search, 1, 0);
            top.Controls.Add(lblCount, 2, 0);

            var split = new SplitContainer { Dock = DockStyle.Fill, FixedPanel = FixedPanel.Panel1 };
            split.Panel1.Padding = new Padding(4);
            split.Panel1.Controls.Add(tree);

            var buttons = new FlowLayoutPanel { Dock = DockStyle.Bottom, FlowDirection = FlowDirection.RightToLeft, AutoSize = true, Padding = new Padding(4) };
            buttons.Controls.Add(btnInsert);
            buttons.Controls.Add(btnCopy);
            buttons.Controls.Add(new Label { Width = 16 });
            buttons.Controls.Add(btnInsertExample);
            buttons.Controls.Add(btnCopyExample);
            var infoPanel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(8), BackColor = SystemColors.Window };
            infoPanel.Controls.Add(info);
            split.Panel2.Controls.Add(infoPanel);
            split.Panel2.Controls.Add(buttons);

            Controls.Add(split);
            Controls.Add(top);

            search.TextChanged += (o, e) => { searchDelay.Stop(); searchDelay.Start(); };
            searchDelay.Tick += (o, e) => { searchDelay.Stop(); Fill(); };
            search.KeyDown += (o, e) =>
            {
                if (e.KeyCode == Keys.Down && tree.Nodes.Count > 0)
                {
                    tree.Focus();
                    tree.SelectedNode = FirstCommand(tree.Nodes) ?? tree.Nodes[0];
                    e.Handled = true;
                }
            };
            tree.AfterSelect += (o, e) => ShowCommand(e.Node.Tag as uint?);
            tree.NodeMouseDoubleClick += (o, e) => { if (e.Node.Tag is uint) Insert(); };
            tree.KeyDown += (o, e) => { if (e.KeyCode == Keys.Enter && tree.SelectedNode?.Tag is uint) { Insert(); e.Handled = true; } };
            btnInsert.Click += (o, e) => Insert();
            btnCopy.Click += (o, e) => { if (current.HasValue) Clipboard.SetText(Template(current.Value)); };
            btnInsertExample.Click += (o, e) => InsertExample();
            btnCopyExample.Click += (o, e) => { if (current.HasValue) Clipboard.SetText(string.Join(Environment.NewLine, ACMD_INFO.GetExample(current.Value))); };
            var tips = new ToolTip();
            tips.SetToolTip(btnInsert, "Adds this command on a new line below the caret in the open script (or double-click / Enter in the list).");
            tips.SetToolTip(btnInsertExample, "Adds the example (with its // comments) below the caret in the open script.");
            Activated += (o, e) => UpdateButtons();
            Load += (o, e) => split.SplitterDistance = 340;   // once the window has its size

            Fill();
            ShowCommand(null);
        }

        static int GroupRank(string group)
        {
            int i = Array.IndexOf(GroupOrder, group);
            return i >= 0 ? i : group == "Other" ? int.MaxValue : GroupOrder.Length;
        }

        static string[] Syntax(uint crc)
        {
            string s;
            return ACMD_INFO.PARAM_SYNTAX.TryGetValue(crc, out s) && !string.IsNullOrEmpty(s) && s != "NONE"
                ? s.Split(',').Select(x => x.Trim()).ToArray() : new string[0];
        }

        static int[] Format(uint crc)
        {
            string f;
            return ACMD_INFO.PARAM_FORMAT.TryGetValue(crc, out f) && !string.IsNullOrEmpty(f) && f != "NONE"
                ? f.Split(',').Select(x => int.Parse(x.Trim())).ToArray() : new int[0];
        }

        bool Matches(uint crc, string[] words)
        {
            if (words.Length == 0)
                return true;
            var text = string.Join(" ", new[] { ACMD_INFO.CMD_NAMES[crc], crc.ToString("X8"), ACMD_INFO.GetDescription(crc),
                ACMD_INFO.GetCategory(crc) }.Concat(Syntax(crc)));
            Dictionary<string, string> pd;
            if (ACMD_INFO.PARAM_DESC.TryGetValue(crc, out pd))
                text += " " + string.Join(" ", pd.Values);
            return words.All(w => text.IndexOf(w, StringComparison.OrdinalIgnoreCase) >= 0);
        }

        void Fill()
        {
            var words = search.Text.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(w => w.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? w.Substring(2) : w).ToArray();
            var groups = ACMD_INFO.CMD_NAMES.Keys.Where(c => Matches(c, words))
                .GroupBy(ACMD_INFO.GetCategory)
                .OrderBy(g => GroupRank(g.Key)).ThenBy(g => g.Key, StringComparer.OrdinalIgnoreCase);
            uint? keep = current;
            TreeNode select = null;
            int total = 0;
            tree.BeginUpdate();
            tree.Nodes.Clear();
            foreach (var g in groups)
            {
                var cmds = g.OrderBy(c => ACMD_INFO.CMD_NAMES[c].StartsWith("unk_") ? 1 : 0)
                    .ThenBy(c => ACMD_INFO.CMD_NAMES[c], StringComparer.OrdinalIgnoreCase).ToList();
                var node = new TreeNode($"{g.Key} ({cmds.Count})");
                foreach (var c in cmds)
                {
                    var n = new TreeNode(ACMD_INFO.CMD_NAMES[c]) { Tag = c, ToolTipText = FirstSentence(ACMD_INFO.GetDescription(c)) };
                    if (ACMD_INFO.CMD_NAMES[c].StartsWith("unk_"))
                        n.ForeColor = Color.Gray;
                    node.Nodes.Add(n);
                    if (keep == c)
                        select = n;
                }
                total += cmds.Count;
                tree.Nodes.Add(node);
                if (words.Length > 0)
                    node.Expand();
            }
            tree.EndUpdate();
            lblCount.Text = $"{total} of {ACMD_INFO.CMD_NAMES.Count} commands";
            if (select != null)
            {
                tree.SelectedNode = select;
                select.EnsureVisible();
            }
        }

        static TreeNode FirstCommand(TreeNodeCollection nodes)
        {
            foreach (TreeNode n in nodes)
            {
                if (n.Tag is uint)
                    return n;
                var c = FirstCommand(n.Nodes);
                if (c != null)
                    return c;
            }
            return null;
        }

        static string FirstSentence(string text)
        {
            if (string.IsNullOrEmpty(text))
                return null;
            int br = text.IndexOfAny(new[] { '\r', '\n' });
            if (br > 0)
                text = text.Substring(0, br);
            int i = text.IndexOf(". ", StringComparison.Ordinal);
            text = i > 0 ? text.Substring(0, i + 1) : text;
            return text.Length > 200 ? text.Substring(0, 200) + "…" : text;
        }

        /// <summary>The command with every parameter named and 0 (what Insert / Copy give).</summary>
        static string Template(uint crc)
        {
            var syntax = Syntax(crc);
            var format = Format(crc);
            var parts = new List<string>();
            for (int i = 0; i < format.Length; i++)
            {
                string value = format[i] == 1 || format[i] == 2 ? "0.0" : "0";
                parts.Add(i < syntax.Length && syntax[i].Length > 0 ? $"{syntax[i]}={value}" : value);
            }
            return $"{ACMD_INFO.CMD_NAMES[crc]}({string.Join(", ", parts)})";
        }

        static readonly Font body = new Font(SystemFonts.MessageBoxFont.FontFamily, 9.5f);
        static readonly Font bold = new Font(body, FontStyle.Bold);
        static readonly Font title = new Font(body.FontFamily, 14f, FontStyle.Bold);
        static readonly Font mono = new Font(FontFamily.GenericMonospace, 9f);

        void ShowCommand(uint? crc)
        {
            current = crc;
            info.Clear();
            Action<string, Font, Color> add = (t, f, color) =>
            {
                info.SelectionStart = info.TextLength;
                info.SelectionFont = f;
                info.SelectionColor = color;
                info.AppendText(t);
            };
            if (!crc.HasValue)
            {
                add("Pick a command on the left.\n\n", body, SystemColors.WindowText);
                add("Commands are grouped by what they do. Search finds a command by its name, identifier, " +
                    "description or parameters (e.g. \"knockback\", \"sound\", \"B738EABD\"). Gray commands " +
                    "(unk_) have no known name.\n\nInsert (or double-click, or Enter) adds the command to the " +
                    "open script below the caret, with every parameter set to 0. Most commands also have an example: " +
                    "a real use from the game's scripts (or, for the new commands, a hand-written one), which " +
                    "Insert Example adds to the script.", body, Color.DimGray);
                UpdateButtons();
                return;
            }
            uint c = crc.Value;
            add(ACMD_INFO.CMD_NAMES[c] + "\n", title, SystemColors.WindowText);
            add($"{ACMD_INFO.GetCategory(c)}  ·  identifier 0x{c:X8}\n\n", body, Color.DimGray);
            var desc = ACMD_INFO.GetDescription(c);
            add(string.IsNullOrEmpty(desc) ? "No description.\n\n" : desc + "\n\n", body,
                string.IsNullOrEmpty(desc) ? Color.DimGray : SystemColors.WindowText);

            var syntax = Syntax(c);
            var format = Format(c);
            add(format.Length == 0 ? "No parameters.\n\n" : $"Parameters ({format.Length})\n", bold, SystemColors.WindowText);
            for (int i = 0; i < format.Length; i++)
            {
                string name = i < syntax.Length ? syntax[i] : "Unknown";
                add($"{i + 1}. {name}", bold, SystemColors.WindowText);
                add($"  ({(format[i] >= 0 && format[i] < TypeNames.Length ? TypeNames[format[i]] : "?")})", body, Color.DimGray);
                var pd = ACMD_INFO.GetParamDescription(c, name);
                add(string.IsNullOrEmpty(pd) ? "\n" : "\n    " + pd + "\n", body, SystemColors.WindowText);
            }
            if (format.Length > 0)
                add("\n", body, SystemColors.WindowText);
            add("Template\n", bold, SystemColors.WindowText);
            add(Template(c) + "\n", mono, Color.DarkBlue);
            var example = ACMD_INFO.GetExample(c);
            if (example.Count > 0)
            {
                add("\nExample\n", bold, SystemColors.WindowText);
                foreach (var line in example)
                    add(line + "\n", mono, line.TrimStart().StartsWith("//") ? Color.SeaGreen : Color.DarkBlue);
            }
            info.SelectionStart = 0;
            info.ScrollToCaret();
            UpdateButtons();
        }

        void UpdateButtons()
        {
            btnCopy.Enabled = current.HasValue;
            btnInsert.Enabled = current.HasValue && activeEditor?.Invoke() != null;
            bool hasExample = current.HasValue && ACMD_INFO.GetExample(current.Value).Count > 0;
            btnCopyExample.Enabled = hasExample;
            btnInsertExample.Enabled = hasExample && activeEditor?.Invoke() != null;
        }

        void Insert()
        {
            if (current.HasValue)
                InsertText(Template(current.Value));
        }

        void InsertExample()
        {
            if (current.HasValue && ACMD_INFO.GetExample(current.Value).Count > 0)
                InsertText(string.Join("\n", ACMD_INFO.GetExample(current.Value)));
        }

        void InsertText(string text)
        {
            var editor = activeEditor?.Invoke();
            if (editor == null)
            {
                MessageBox.Show(this, "Open an ACMD script first (the command is added at its caret). Copy puts it on the clipboard instead.",
                    "No script open", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            editor.InsertCommandLine(text);
            editor.FindForm()?.Activate();
            editor.Focus();
        }
    }
}
