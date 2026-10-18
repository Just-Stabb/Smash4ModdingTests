using FastColoredTextBoxNS;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Classes;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using SALT.Moveset;

namespace Sm4shCommand
{
    public class ITS_EDITOR : FastColoredTextBox
    {
        TextStyle keywordStyle = new TextStyle(Brushes.Blue, null, FontStyle.Regular);
        TextStyle HexStyle = new TextStyle(Brushes.DarkCyan, null, FontStyle.Regular);
        TextStyle DecStyle = new TextStyle(Brushes.Red, null, FontStyle.Regular);
        TextStyle StrStyle = new TextStyle(Brushes.Chocolate, null, FontStyle.Regular);
        TextStyle ArrStyle = new TextStyle(Brushes.Blue, null, FontStyle.Regular);
        TextStyle CommentStyle = new TextStyle(Brushes.DarkGreen, null, FontStyle.Regular);
        TextStyle LinkStyle = new TextStyle(Brushes.DarkBlue, null, FontStyle.Underline);

        // JUMP(Hash=0x...) / CALL(Hash=0x...): the hash is a link to that script (Ctrl+click).
        static readonly Regex LinkRegex = new Regex(@"\b(?:JUMP|CALL)\s*\(\s*(?:Hash\s*=\s*)?(0x[0-9A-Fa-f]+)", RegexOptions.IgnoreCase);

        /// <summary>
        /// Raised when a JUMP/CALL target is Ctrl+clicked; the main window opens that script.
        /// </summary>
        public static event Action<uint> OpenScriptRequested;

        public AutocompleteMenu AutocompleteMenu { get; set; }

        public ITS_EDITOR()
        {
            this.TextChanged += NewBox_TextChanged;
            this.AutoCompleteBrackets = true;
            this.AutoIndent = true;
            this.ToolTipNeeded += Editor_ToolTipNeeded;
            this.MouseDown += Editor_MouseDown;
            this.MouseMove += Editor_MouseMove;
            this.ToolTipDelay = 400;
            BuildContextMenu();
        }
        public ITS_EDITOR(IScript script) : this()
        {
            Script = script;
            Text = ScriptComments.TextFor(script);  // with its comments (.comments file), if any
            IsChanged = false;
        }
        public ITS_EDITOR(IScript script, string[] autocomplete) : this()
        {
            Script = script;
            Text = ScriptComments.TextFor(script);
            IsChanged = false;
            if (autocomplete != null)
            {
                this.AutocompleteMenu = new AutocompleteMenu(this) { AppearInterval = 1 };
                this.AutocompleteMenu.Items.SetAutocompleteItems(autocomplete);
                this.AutoCompleteBrackets = true;
                this.AutoIndent = true;
            }
        }
        public ITS_EDITOR(SALT.Moveset.MSC.MSCScript script, bool legacy) : this()
        {
            Script = script;
            if (legacy)
                Text = script.Deserialize();
            else
                Text = script.Decompile();
            IsChanged = false;
        }
        public IScript Script { get; set; }

        /// <summary>
        /// Compiles the text into the script. Throws if the text doesn't compile (the script is
        /// left unchanged then); use <see cref="TryApplyChanges"/> to get the error instead.
        /// </summary>
        public void ApplyChanges()
        {
            Script.Serialize(Text);
            ScriptComments.Remember(Script, Text);  // the .bin has no room for comments
            IsChanged = false;
        }

        /// <summary>
        /// Compiles the text into the script. On an error, selects the offending line and returns
        /// false with a message for the user; the script is left unchanged.
        /// </summary>
        public bool TryApplyChanges(out string error)
        {
            error = null;
            if (!IsChanged)
                return true;
            try
            {
                ApplyChanges();
                return true;
            }
            catch (ACMDCompileException e)
            {
                int line = FindLine(e.LineText);
                error = line >= 0 ? $"Line {line + 1}: {e.Reason}\n    {e.LineText.Trim()}" : e.Message;
                if (line >= 0)
                {
                    Selection = new Range(this, 0, line, GetLineLength(line), line);
                    DoSelectionVisible();
                }
                return false;
            }
            catch (Exception e)
            {
                error = e.Message;
                return false;
            }
        }

        int FindLine(string lineText)
        {
            if (string.IsNullOrEmpty(lineText))
                return -1;
            var want = lineText.Trim();
            for (int i = 0; i < LinesCount; i++)
            {
                var code = ACMDCompiler.StripComments(new[] { Lines[i] });
                if (Lines[i].Trim() == want || code.Count == 1 && code[0] == want)
                    return i;
            }
            return -1;
        }

        private void NewBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            //clear previous highlighting
            e.ChangedRange.ClearStyle(StyleIndex.All);
            //highlight tags
            e.ChangedRange.SetStyle(CommentStyle, @"//.*$", RegexOptions.Multiline);
            Range.SetStyle(CommentStyle, @"/\*[\s\S]*?\*/", RegexOptions.Multiline);
            e.ChangedRange.SetStyle(LinkStyle, @"(?<=\b(?:JUMP|CALL)\s*\(\s*(?:Hash\s*=\s*)?)0x[0-9A-Fa-f]+", RegexOptions.IgnoreCase);
            e.ChangedRange.SetStyle(keywordStyle, @"\b(if|else|try|catch)\b");
            //e.ChangedRange.SetStyle(keywordStyle, @"(?<=[\(,])+[^=)]+(?==)\b");
            e.ChangedRange.SetStyle(HexStyle, @"0x[^\)\s,\r\n]+");
            e.ChangedRange.SetStyle(DecStyle, @"\b(?:[0-9]*\\.)?[0-9]+\b");
            e.ChangedRange.SetStyle(StrStyle, "\"(\\.|[^\"])*\"");
            e.ChangedRange.SetStyle(ArrStyle, @"([A-Za-z\x5F\x2D]+)-.{1,5}\[[0-F0-f]+\]");
        }

        // ------------------------------------------------------------------ links

        /// <summary>
        /// The JUMP/CALL target under a text position, or null.
        /// </summary>
        uint? LinkAt(Place place)
        {
            if (place.iLine < 0 || place.iLine >= LinesCount)
                return null;
            foreach (Match m in LinkRegex.Matches(Lines[place.iLine]))
            {
                var g = m.Groups[1];
                if (place.iChar >= g.Index && place.iChar <= g.Index + g.Length)
                {
                    uint crc;
                    if (uint.TryParse(g.Value.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out crc))
                        return crc;
                }
            }
            return null;
        }

        private void Editor_MouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button != MouseButtons.Left || (ModifierKeys & Keys.Control) == 0)
                return;
            var crc = LinkAt(PointToPlace(e.Location));
            if (crc.HasValue)
                OpenScriptRequested?.Invoke(crc.Value);
        }

        bool _handCursor;
        private void Editor_MouseMove(object sender, MouseEventArgs e)
        {
            bool link = (ModifierKeys & Keys.Control) != 0 && LinkAt(PointToPlace(e.Location)).HasValue;
            if (link && !_handCursor)
                Cursor = Cursors.Hand;
            else if (!link && _handCursor)
                Cursor = Cursors.IBeam;
            _handCursor = link;
        }

        // --------------------------------------------------------------- tooltips

        /// <summary>What's at a text position: the command on the line, the parameter the position is
        /// in (name and index, when the command has definitions) and the number written there.</summary>
        class Spot
        {
            public uint Crc;
            public bool HasCommand;
            public string Command, Param, Token;
            public string Type { get { return ParamIndex >= 0 && ParamIndex < Types.Length ? TypeName(Types[ParamIndex]) : null; } }
            public int ParamIndex = -1;
            public string[] Syntax = new string[0], Types = new string[0];
        }

        Spot SpotAt(Place place)
        {
            var spot = new Spot();
            if (place.iLine < 0 || place.iLine >= LinesCount)
                return spot;
            string line = Lines[place.iLine];
            int col = place.iChar;
            spot.Token = NumberAt(line, col);

            // The command on this line: the identifier before the first '('.
            int open = line.IndexOf('(');
            if (open < 0)
                return spot;
            string name = line.Substring(0, open).Trim();
            if (name.StartsWith("if", StringComparison.OrdinalIgnoreCase) || name.StartsWith("else", StringComparison.OrdinalIgnoreCase))
            {
                // if(Float_Var_Compare(...)): the command is the one inside
                int open2 = line.IndexOf('(', open + 1);
                if (open2 > 0)
                {
                    name = line.Substring(open + 1, open2 - open - 1).Trim();
                    open = open2;
                }
            }
            uint crc;
            if (!ACMD_INFO.TryGetIdent(name, out crc))
                return spot;
            spot.Crc = crc;
            spot.HasCommand = true;
            spot.Command = ACMD_INFO.CMD_NAMES[crc];
            spot.Syntax = ACMD_INFO.PARAM_SYNTAX.ContainsKey(crc) ? ACMD_INFO.PARAM_SYNTAX[crc].Split(',') : new string[0];
            spot.Types = !string.IsNullOrEmpty(ACMD_INFO.PARAM_FORMAT.ContainsKey(crc) ? ACMD_INFO.PARAM_FORMAT[crc] : null)
                ? ACMD_INFO.PARAM_FORMAT[crc].Split(',') : new string[0];
            if (spot.Types.Length == 0)
                spot.Syntax = new string[0];

            // Which parameter the position is in: count commas before it.
            int close = line.IndexOf(')', open);
            if (col > open && (close < 0 || col <= close))
            {
                int index = 0;
                for (int i = open + 1; i < col && i < line.Length; i++)
                    if (line[i] == ',')
                        index++;
                if (index < spot.Syntax.Length)
                {
                    spot.ParamIndex = index;
                    spot.Param = spot.Syntax[index].Trim();
                }
            }
            return spot;
        }

        /// <summary>The integer (0x hex or decimal) written at a column, or null.</summary>
        static string NumberAt(string line, int col)
        {
            // a variable alias (OPP_HITSTUN): letters, digits and _
            Func<char, bool> nameChar = c => char.IsLetterOrDigit(c) || c == '_';
            int ws = Math.Min(col, line.Length), we = ws;
            while (ws > 0 && nameChar(line[ws - 1]))
                ws--;
            while (we < line.Length && nameChar(line[we]))
                we++;
            uint aliased;
            if (we > ws && SALT.Moveset.FighterVariable.TryParseAlias(line.Substring(ws, we - ws), out aliased))
                return line.Substring(ws, we - ws);

            Func<char, bool> part = c => Uri.IsHexDigit(c) || c == 'x' || c == 'X' || c == '-';
            int start = Math.Min(col, line.Length), end = start;
            while (start > 0 && part(line[start - 1]))
                start--;
            while (end < line.Length && part(line[end]))
                end++;
            if (end < line.Length && line[end] == '.') // a float: no tooltip
                return null;
            string word = line.Substring(start, end - start);
            uint v;
            return word.Length > 0 && Tooltips.TryParseValue(word, out v) ? word : null;
        }

        private void Editor_ToolTipNeeded(object sender, ToolTipNeededEventArgs e)
        {
            var link = LinkAt(e.Place);
            if (link.HasValue)
            {
                e.ToolTipTitle = $"Script 0x{link.Value:X8}";
                e.ToolTipText = $"{Runtime.ScriptLabel(link.Value)}\nCtrl+click to open it.";
                return;
            }

            var spot = SpotAt(e.Place);
            string note = spot.Token == null ? "" : Tooltips.Describe(spot.Token, spot.Command, spot.Param, spot.Type, spot.ParamIndex + 1);
            if (!spot.HasCommand)
            {
                if (note.Length > 0)
                {
                    e.ToolTipTitle = spot.Token;
                    e.ToolTipText = note.TrimStart('\n');
                }
                return;
            }

            uint crc = spot.Crc;
            if (spot.ParamIndex >= 0)
            {
                string pname = spot.Param;
                e.ToolTipTitle = $"{spot.Command} \u2192 {pname}";
                string pdesc = ACMD_INFO.GetParamDescription(crc, pname);
                e.ToolTipText = $"Parameter {spot.ParamIndex + 1} of {spot.Syntax.Length}, {TypeName(spot.Types[spot.ParamIndex])}" +
                    (pdesc.Length > 0 ? "\n" + pdesc : "") + note;
                return;
            }

            e.ToolTipTitle = $"{spot.Command}  (0x{crc:X8})";
            string desc = ACMD_INFO.GetDescription(crc);
            string sig = spot.Syntax.Length == 0 ? "No parameters" :
                string.Join(", ", spot.Syntax.Select((x, i) => $"{x}: {TypeName(i < spot.Types.Length ? spot.Types[i] : "0")}").ToArray());
            e.ToolTipText = (desc.Length > 0 ? desc + "\n\n" : "") + sig + note;
        }

        // ------------------------------------------------------- editing tooltips

        Place _menuPlace;

        void BuildContextMenu()
        {
            var menu = new ContextMenuStrip();
            var edit = new ToolStripMenuItem("Edit Tooltip..", null, (o, e) => EditTooltip(_menuPlace));
            menu.Items.Add(edit);
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add(new ToolStripMenuItem("Cut", null, (o, e) => Cut()));
            menu.Items.Add(new ToolStripMenuItem("Copy", null, (o, e) => Copy()));
            menu.Items.Add(new ToolStripMenuItem("Paste", null, (o, e) => Paste()));
            menu.Opening += (o, e) =>
            {
                _menuPlace = PointToPlace(PointToClient(Cursor.Position));
                var spot = SpotAt(_menuPlace);
                edit.Enabled = spot.Token != null;
                edit.Text = spot.Token != null ? $"Edit Tooltip for {spot.Token}.." : "Edit Tooltip.. (right-click a number)";
            };
            ContextMenuStrip = menu;
        }

        void EditTooltip(Place place)
        {
            var spot = SpotAt(place);
            if (spot.Token == null)
                return;
            uint value;
            bool alias = !Tooltips.TryParseValue(spot.Token, out value) && SALT.Moveset.FighterVariable.TryParseAlias(spot.Token, out value);
            var existing = Tooltips.Find(value, spot.Command, spot.Param, spot.Type, spot.ParamIndex + 1).FirstOrDefault();

            using (var f = new Form())
            {
                f.Text = $"Tooltip for {spot.Token}";
                f.FormBorderStyle = FormBorderStyle.FixedDialog;
                f.MinimizeBox = f.MaximizeBox = false;
                f.StartPosition = FormStartPosition.CenterParent;
                f.ClientSize = new Size(420, 268);
                var nameBox = new TextBox { Left = 12, Top = 28, Width = 396, Text = existing?.Name ?? "" };
                var descBox = new TextBox { Left = 12, Top = 76, Width = 396, Height = 90, Multiline = true, ScrollBars = ScrollBars.Vertical, Text = (existing?.Description ?? "").Replace("\n", "\r\n") };
                var inCommand = new CheckBox { Left = 12, Top = 172, Width = 396, Checked = spot.Command != null, Enabled = spot.Command != null, Text = spot.Command != null ? $"Only in {spot.Command}" : "Only in this command" };
                var inParam = new CheckBox { Left = 12, Top = 194, Width = 396, Checked = spot.Param != null, Enabled = spot.Param != null, Text = spot.Param != null ? $"Only in parameter {spot.Param}" : "Only in this parameter" };
                var inFighter = new CheckBox { Left = 12, Top = 216, Width = 396, Checked = false, Enabled = Tooltips.Fighter != null, Text = Tooltips.Fighter != null ? $"Only for {Tooltips.Fighter}" : "Only for this fighter (no fighter open)" };
                var ok = new Button { Text = "Save", Left = 252, Top = 238, Width = 75, DialogResult = DialogResult.OK };
                var cancel = new Button { Text = "Cancel", Left = 333, Top = 238, Width = 75, DialogResult = DialogResult.Cancel };
                f.Controls.AddRange(new Control[] {
                    new Label { Text = "Name:", Left = 12, Top = 10, AutoSize = true }, nameBox,
                    new Label { Text = "Description:", Left = 12, Top = 58, AutoSize = true }, descBox,
                    inCommand, inParam, inFighter, ok, cancel });
                inCommand.Top = 170; inParam.Top = 190; inFighter.Top = 210; ok.Top = cancel.Top = 236;
                f.AcceptButton = ok;
                f.CancelButton = cancel;
                if (f.ShowDialog(FindForm()) != DialogResult.OK || nameBox.Text.Trim().Length == 0)
                    return;
                try
                {
                    Tooltips.SaveCustom(value, nameBox.Text.Trim(), descBox.Text.Trim(),
                        inCommand.Checked ? spot.Command : null, inParam.Checked ? spot.Param : null,
                        inCommand.Checked || inParam.Checked ? null : spot.Type,
                        inFighter.Checked, alias || spot.Token.StartsWith("0x", StringComparison.OrdinalIgnoreCase));
                }
                catch (Exception ex)
                {
                    MessageBox.Show(FindForm(), $"Couldn't save {Tooltips.CustomPath}:\n{ex.Message}", "Edit Tooltip");
                }
            }
        }

        static string TypeName(string type)
        {
            switch (type.Trim())
            {
                case "1": return "float";
                case "2": return "decimal";
                case "3": return "variable";
                default: return "int";
            }
        }
    }
}