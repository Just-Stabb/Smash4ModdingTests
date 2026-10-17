using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using SALT.Moveset.AnimCMD;

namespace Sm4shCommand
{
    /// <summary>
    /// Tools > Command Definitions: view and edit ACMD command definitions (name, parameter names and
    /// types, descriptions shown in tooltips) and add new ones. Saving writes Events.cfg next to the exe,
    /// which is loaded on top of the built-in definitions at startup.
    /// </summary>
    public class CommandDefinitionsForm : Form
    {
        class Def
        {
            public uint Ident;
            public string Name;
            public string Description;
            public List<Param> Params = new List<Param>();
            public bool IsNew;
            public override string ToString() { return Name; }
        }

        class Param
        {
            public string Name;
            public int Type;
            public string Description;
        }

        static readonly string[] TypeNames = { "int", "float", "decimal", "variable" };

        readonly List<Def> defs = new List<Def>();
        readonly TextBox filter = new TextBox { Dock = DockStyle.Top };
        readonly ListBox list = new ListBox { Dock = DockStyle.Fill, IntegralHeight = false };
        readonly TextBox txtIdent = new TextBox { Width = 110 };
        readonly TextBox txtName = new TextBox { Width = 260 };
        readonly TextBox txtDesc = new TextBox { Multiline = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill };
        readonly DataGridView grid = new DataGridView
        {
            Dock = DockStyle.Fill,
            AllowUserToResizeRows = false,
            RowHeadersWidth = 30,
            AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
        };
        readonly Label lblInfo = new Label { AutoSize = true, ForeColor = Color.DimGray };
        Def current;
        bool loading;
        bool dirty;

        public CommandDefinitionsForm()
        {
            Text = "Command Definitions";
            Size = new Size(900, 600);
            StartPosition = FormStartPosition.CenterParent;
            MinimizeBox = false;

            foreach (var pair in ACMD_INFO.CMD_NAMES)
                defs.Add(Load(pair.Key));
            defs.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));

            // left: filter + list
            var left = new Panel { Dock = DockStyle.Left, Width = 260, Padding = new Padding(4) };
            var btnNew = new Button { Text = "New Command", Dock = DockStyle.Bottom, Height = 28 };
            btnNew.Click += (o, e) => NewCommand();
            left.Controls.Add(list);
            left.Controls.Add(filter);
            left.Controls.Add(btnNew);
            filter.TextChanged += (o, e) => RefreshList();
            list.SelectedIndexChanged += (o, e) => Select(list.SelectedItem as Def);

            // right: fields
            var right = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 6, Padding = new Padding(6) };
            right.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            right.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            right.RowStyles.Add(new RowStyle(SizeType.Absolute, 70));
            right.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            right.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            right.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            var top = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Top, WrapContents = false };
            top.Controls.Add(new Label { Text = "Identifier (hex)", AutoSize = true, Margin = new Padding(0, 6, 4, 0) });
            top.Controls.Add(txtIdent);
            top.Controls.Add(new Label { Text = "Name", AutoSize = true, Margin = new Padding(12, 6, 4, 0) });
            top.Controls.Add(txtName);
            right.Controls.Add(top);
            right.Controls.Add(new Label { Text = "Description (shown when hovering the command in the editor)", AutoSize = true, Margin = new Padding(0, 8, 0, 2) });
            right.Controls.Add(txtDesc);
            right.Controls.Add(new Label
            {
                Text = "Parameters, in order (types: int, float, decimal, variable). Descriptions show when hovering the parameter.",
                AutoSize = true,
                Margin = new Padding(0, 8, 0, 2)
            });
            right.Controls.Add(grid);

            var bottom = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft };
            var btnClose = new Button { Text = "Close", Width = 90 };
            var btnSave = new Button { Text = "Save to Events.cfg", Width = 140 };
            btnClose.Click += (o, e) => Close();
            btnSave.Click += (o, e) => Save();
            bottom.Controls.Add(btnClose);
            bottom.Controls.Add(btnSave);
            bottom.Controls.Add(lblInfo);
            right.Controls.Add(bottom);

            grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Name", FillWeight = 30 });
            var typeCol = new DataGridViewComboBoxColumn { HeaderText = "Type", FillWeight = 15, FlatStyle = FlatStyle.Flat };
            typeCol.Items.AddRange(TypeNames);
            grid.Columns.Add(typeCol);
            grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Description", FillWeight = 55 });
            grid.CellValueChanged += (o, e) => { if (!loading) { StoreGrid(); } };
            grid.UserDeletedRow += (o, e) => { if (!loading) StoreGrid(); };
            grid.CurrentCellDirtyStateChanged += (o, e) => { if (grid.IsCurrentCellDirty) grid.CommitEdit(DataGridViewDataErrorContexts.Commit); };
            grid.DataError += (o, e) => { e.ThrowException = false; };

            txtName.TextChanged += (o, e) => { if (!loading && current != null) { current.Name = txtName.Text.Trim(); dirty = true; } };
            txtDesc.TextChanged += (o, e) => { if (!loading && current != null) { current.Description = txtDesc.Text; dirty = true; } };
            txtIdent.TextChanged += (o, e) =>
            {
                if (loading || current == null || !current.IsNew)
                    return;
                uint v;
                var t = txtIdent.Text.Trim();
                if (t.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                    t = t.Substring(2);
                if (uint.TryParse(t, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out v))
                {
                    current.Ident = v;
                    dirty = true;
                }
            };

            Controls.Add(right);
            Controls.Add(left);
            RefreshList();
            FormClosing += (o, e) =>
            {
                if (!dirty)
                    return;
                var answer = MessageBox.Show(this, "Save your changes to Events.cfg?", Text, MessageBoxButtons.YesNoCancel, MessageBoxIcon.Question);
                if (answer == DialogResult.Cancel)
                    e.Cancel = true;
                else if (answer == DialogResult.Yes && !Save())
                    e.Cancel = true;
            };
        }

        static Def Load(uint crc)
        {
            var d = new Def { Ident = crc, Name = ACMD_INFO.CMD_NAMES[crc], Description = ACMD_INFO.GetDescription(crc) };
            string format, syntax;
            ACMD_INFO.PARAM_FORMAT.TryGetValue(crc, out format);
            ACMD_INFO.PARAM_SYNTAX.TryGetValue(crc, out syntax);
            if (!string.IsNullOrEmpty(format) && format != "NONE")
            {
                var types = format.Split(',');
                var names = string.IsNullOrEmpty(syntax) || syntax == "NONE" ? new string[0] : syntax.Split(',');
                for (int i = 0; i < types.Length; i++)
                {
                    int t;
                    int.TryParse(types[i].Trim(), out t);
                    string n = i < names.Length ? names[i].Trim() : "Unknown";
                    d.Params.Add(new Param { Name = n, Type = t, Description = ACMD_INFO.GetParamDescription(crc, n) });
                }
            }
            return d;
        }

        void RefreshList()
        {
            var keep = current;
            var f = filter.Text.Trim();
            list.BeginUpdate();
            list.Items.Clear();
            foreach (var d in defs)
                if (f.Length == 0 || d.Name.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0 ||
                    d.Ident.ToString("X8").IndexOf(f.Replace("0x", ""), StringComparison.OrdinalIgnoreCase) >= 0)
                    list.Items.Add(d);
            list.EndUpdate();
            if (keep != null && list.Items.Contains(keep))
                list.SelectedItem = keep;
        }

        void Select(Def d)
        {
            if (d == null)
                return;
            current = d;
            loading = true;
            txtIdent.Text = d.Ident.ToString("X8");
            txtIdent.ReadOnly = !d.IsNew;
            txtName.Text = d.Name;
            txtDesc.Text = d.Description ?? "";
            grid.Rows.Clear();
            foreach (var p in d.Params)
                grid.Rows.Add(p.Name, TypeNames[Math.Max(0, Math.Min(3, p.Type))], p.Description ?? "");
            grid.AllowUserToAddRows = d.IsNew;
            grid.AllowUserToDeleteRows = d.IsNew;
            lblInfo.Text = d.IsNew
                ? "New command: set its identifier and parameters (the parameter count sets its size)."
                : "The parameter count of an existing command is fixed (it sets how files are read).";
            loading = false;
        }

        void StoreGrid()
        {
            if (current == null)
                return;
            var ps = new List<Param>();
            foreach (DataGridViewRow row in grid.Rows)
            {
                if (row.IsNewRow)
                    continue;
                string name = Convert.ToString(row.Cells[0].Value ?? "").Trim();
                int type = Array.IndexOf(TypeNames, Convert.ToString(row.Cells[1].Value ?? "int"));
                ps.Add(new Param { Name = name.Length == 0 ? "Unknown" : name, Type = type < 0 ? 0 : type, Description = Convert.ToString(row.Cells[2].Value ?? "").Trim() });
            }
            current.Params = ps;
            dirty = true;
        }

        void NewCommand()
        {
            var d = new Def { Ident = 0, Name = "New_Command", Description = "", IsNew = true };
            defs.Add(d);
            filter.Text = "";
            RefreshList();
            list.SelectedItem = d;
            txtIdent.Focus();
            dirty = true;
        }

        bool Save()
        {
            StoreGrid();
            // validate
            var seen = new Dictionary<uint, Def>();
            foreach (var d in defs)
            {
                if (string.IsNullOrEmpty(d.Name) || d.Name.IndexOfAny(new[] { '(', ')', ',', '=', ' ' }) >= 0)
                    return Fail(d, $"\"{d.Name}\" isn't a valid command name (no spaces, brackets, commas or =).");
                if (d.Params.Any(p => p.Name.IndexOfAny(new[] { ',', '=', '(', ')' }) >= 0))
                    return Fail(d, $"{d.Name}: parameter names can't contain , = ( or ).");
                if (d.IsNew && d.Ident == 0)
                    return Fail(d, $"{d.Name}: set the identifier (the command's hex CRC32 from the file).");
                if (seen.ContainsKey(d.Ident))
                    return Fail(d, $"{d.Name} and {seen[d.Ident].Name} have the same identifier {d.Ident:X8}.");
                seen[d.Ident] = d;
            }

            foreach (var d in defs)
            {
                var pdesc = d.Params.Where(p => !string.IsNullOrEmpty(p.Description))
                    .GroupBy(p => p.Name).ToDictionary(g => g.Key, g => g.First().Description);
                int size = d.IsNew || !ACMD_INFO.CMD_SIZES.ContainsKey(d.Ident) ? d.Params.Count + 1 : ACMD_INFO.CMD_SIZES[d.Ident];
                ACMD_INFO.SetCMDInfo(d.Ident, size, d.Name, d.Params.Select(p => p.Type).ToArray(),
                    d.Params.Select(p => p.Name).ToArray(), d.Description, pdesc);
                d.IsNew = false;
            }

            var path = Path.Combine(Application.StartupPath, "Events.cfg");
            try
            {
                ACMD_INFO.SaveInfo(path);
            }
            catch (Exception e)
            {
                MessageBox.Show(this, $"Couldn't write {path}:\n{e.Message}", Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
            dirty = false;
            Select(current);
            lblInfo.Text = $"Saved to {path}. Reopen script tabs to see renamed commands.";
            return true;
        }

        bool Fail(Def d, string message)
        {
            filter.Text = "";
            RefreshList();
            list.SelectedItem = d;
            MessageBox.Show(this, message, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return false;
        }
    }
}
