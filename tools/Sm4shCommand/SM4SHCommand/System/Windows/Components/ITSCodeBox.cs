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
        ColorPreviewStyle ColorStyle = new ColorPreviewStyle();

        // JUMP(Hash=0x...) / CALL(Hash=0x...): the hash is a link to that script (Ctrl+click).
        static readonly Regex LinkRegex = new Regex(@"\b(?:JUMP|CALL)\s*\(\s*(?:Hash\s*=\s*)?(0x[0-9A-Fa-f]+)", RegexOptions.IgnoreCase);

        /// <summary>
        /// Raised when a JUMP/CALL target is Ctrl+clicked; the main window opens that script.
        /// </summary>
        public static event Action<uint> OpenScriptRequested;

        public AutocompleteMenu AutocompleteMenu { get; set; }

        // ---------------------------------------------------------------- parameter jump
        //
        // View > Jump Between Parameters: ParamJumpKey (Tab by default) selects the next parameter's
        // value on the line (Shift + the key: the previous one), so typing replaces it; past the line's
        // last parameter it goes on to the next line that has some. Off: the key does what it did.

        public static bool ParamJumpEnabled;
        public static Keys ParamJumpKey = Keys.Tab;

        public override bool ProcessKey(Keys keyData)
        {
            if (ParamJumpEnabled && (keyData & Keys.KeyCode) == ParamJumpKey && (keyData & (Keys.Control | Keys.Alt)) == 0
                && JumpToParameter((keyData & Keys.Shift) != 0))
                return true;
            return base.ProcessKey(keyData);
        }

        /// <summary>
        /// The value spans (start, end: character indices) of a line's parameters: the text after
        /// "Name=" (or the whole parameter without a name) up to the next ',' or ')', trimmed, in every
        /// parameter list on the line (a parameter that holds a call, as if(Bit_Variable_Test(...)),
        /// gives its call's values instead). Nothing for a line without one; "//" ends the line.
        /// </summary>
        public static List<Tuple<int, int>> ParameterValues(string line)
        {
            var spans = new List<Tuple<int, int>>();
            int comment = line.IndexOf("//", StringComparison.Ordinal);
            if (comment >= 0)
                line = line.Substring(0, comment);
            var start = new Stack<int>();       // the open lists' current parameter starts
            var nested = new Stack<bool>();     // ... and whether that parameter holds a list
            bool quoted = false;
            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (c == '"')
                    quoted = !quoted;
                if (quoted)
                    continue;
                if (c == '(' || c == '[')
                {
                    if (nested.Count > 0)
                    {
                        nested.Pop();
                        nested.Push(true);
                    }
                    start.Push(i + 1);
                    nested.Push(false);
                }
                else if (start.Count > 0 && (c == ',' || c == ')' || c == ']'))
                {
                    if (!nested.Pop())
                        AddValue(line, start.Peek(), i, spans);
                    start.Pop();
                    if (c == ',')
                    {
                        start.Push(i + 1);
                        nested.Push(false);
                    }
                }
            }
            return spans;
        }

        static void AddValue(string line, int from, int to, List<Tuple<int, int>> spans)
        {
            int eq = line.IndexOf('=', from, to - from);
            int s = eq >= 0 ? eq + 1 : from, e = to;
            while (s < e && char.IsWhiteSpace(line[s])) s++;
            while (e > s && char.IsWhiteSpace(line[e - 1])) e--;
            if (e > s)
                spans.Add(Tuple.Create(s, e));
        }

        /// <summary>
        /// Selects the next (or previous) parameter value from the caret; false if the script has none.
        /// </summary>
        public bool JumpToParameter(bool back)
        {
            var sel = Selection.Clone();
            sel.Normalize();
            int line = sel.Start.iLine, at = sel.Start.iChar;
            bool empty = sel.IsEmpty;
            for (int n = 0; n < LinesCount; n++)
            {
                int l = back ? line - n : line + n;
                if (l < 0 || l >= LinesCount)
                    break;
                var spans = ParameterValues(Lines[l]);
                if (spans.Count == 0)
                    continue;
                Tuple<int, int> pick;
                if (n == 0)
                    pick = back ? spans.LastOrDefault(s => s.Item1 < at)
                                : spans.FirstOrDefault(s => s.Item1 > at || s.Item1 == at && empty);
                else
                    pick = back ? spans.Last() : spans.First();
                if (pick == null)
                    continue;
                Selection = new Range(this, pick.Item1, l, pick.Item2, l);
                DoSelectionVisible();
                return true;
            }
            return false;
        }

        /// <summary>
        /// Adds a line below the caret's line (in its place if it's blank), indented like it, and selects
        /// the new line's first parameter value. One undo step. Used by View > Commands.
        /// </summary>
        public void InsertCommandLine(string text)
        {
            int l = Math.Max(0, Math.Min(Selection.Start.iLine, LinesCount - 1));
            string cur = LinesCount > 0 ? Lines[l] : "";
            string indent = cur.Substring(0, cur.Length - cur.TrimStart().Length);
            int target;
            if (cur.Trim().Length == 0)
            {
                Selection = new Range(this, 0, l, cur.Length, l);
                InsertText(indent + text);
                target = l;
            }
            else
            {
                Selection = new Range(this, cur.Length, l, cur.Length, l);
                InsertText("\n" + indent + text);
                target = l + 1;
            }
            var spans = ParameterValues(Lines[target]);
            if (spans.Count > 0)
                Selection = new Range(this, spans[0].Item1, target, spans[0].Item2, target);
            DoSelectionVisible();
        }

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
            ClearUndo(); // loading isn't an edit: undoing it used to empty the script
        }
        public ITS_EDITOR(IScript script, string[] autocomplete) : this()
        {
            Script = script;
            Text = ScriptComments.TextFor(script);
            IsChanged = false;
            ClearUndo();
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
            ClearUndo();
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
            var colorNames = ColorCommandPattern();
            if (colorNames != null)
                e.ChangedRange.SetStyle(ColorStyle, colorNames);
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
            var pick = new ToolStripMenuItem("Pick Color..", null, (o, e) => PickColor(_menuPlace.iLine));
            menu.Items.Add(pick);
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
                var c = _menuPlace.iLine >= 0 && _menuPlace.iLine < LinesCount ? ColorParams.Find(Lines[_menuPlace.iLine]) : null;
                pick.Enabled = c != null;
                pick.Text = c != null ? $"Pick Color for {c.Command}.." : "Pick Color.. (right-click a command with R, G, B)";
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

        // ---------------------------------------------------------------- colors

        /// <summary>A regex matching the names of the commands that have R, G, B parameters (or null).</summary>
        static Regex ColorCommandPattern()
        {
            var names = ACMD_INFO.CMD_NAMES.Where(x => ColorParams.Indexes(x.Key) != null).Select(x => Regex.Escape(x.Value)).ToArray();
            return names.Length == 0 ? null : new Regex(@"\b(?:" + string.Join("|", names) + @")(?=\s*\()");
        }

        /// <summary>Right-click > Pick Color: a color dialog that fills in the line's R, G, B.</summary>
        void PickColor(int iLine)
        {
            if (iLine < 0 || iLine >= LinesCount)
                return;
            var c = ColorParams.Find(Lines[iLine]);
            if (c == null)
                return;
            using (var dlg = new ColorDialog { FullOpen = true, AnyColor = true })
            {
                Color current;
                if (c.TryGetColor(out current))
                    dlg.Color = current;
                if (dlg.ShowDialog(FindForm()) != DialogResult.OK)
                    return;
                string line = c.WithColor(dlg.Color);
                Selection = new Range(this, 0, iLine, GetLineLength(iLine), iLine);
                InsertText(line); // one undo step
            }
        }

        /// <summary>
        /// Finds a command's R, G, B parameters (named R/G/B or Red/Green/Blue in its definition) on a
        /// line and reads / writes them. Values 0-255; when all three are written as 0-1 (0.5, 1.0) the
        /// line is taken to use that scale. Floats, hex float bits (0x437A0000) and ints are read.
        /// </summary>
        public class ColorParams
        {
            public string Command, Line;
            int[] _idx;
            List<int[]> _spans; // value start, length, per parameter
            bool[] _float;

            public static int[] Indexes(uint crc)
            {
                string syn;
                if (!ACMD_INFO.PARAM_SYNTAX.TryGetValue(crc, out syn) || string.IsNullOrEmpty(syn))
                    return null;
                var names = syn.Split(',').Select(x => x.Trim().ToLowerInvariant()).ToList();
                Func<string, string, int> at = (a, b) => names.IndexOf(a) >= 0 ? names.IndexOf(a) : names.IndexOf(b);
                int r = at("r", "red"), g = at("g", "green"), bl = at("b", "blue");
                return r < 0 || g < 0 || bl < 0 ? null : new[] { r, g, bl };
            }

            public static ColorParams Find(string line)
            {
                int open = line.IndexOf('(');
                if (open < 0)
                    return null;
                uint crc;
                if (!ACMD_INFO.TryGetIdent(line.Substring(0, open).Trim(), out crc))
                    return null;
                var idx = Indexes(crc);
                if (idx == null)
                    return null;
                int close = line.IndexOf(')', open);
                if (close < 0)
                    close = line.Length;
                var spans = new List<int[]>();
                int start = open + 1;
                for (int i = open + 1; i <= close; i++)
                {
                    if (i == close || line[i] == ',')
                    {
                        int vs = start, ve = i;
                        int eq = line.IndexOf('=', vs, ve - vs);
                        if (eq >= 0)
                            vs = eq + 1;
                        while (vs < ve && char.IsWhiteSpace(line[vs])) vs++;
                        while (ve > vs && char.IsWhiteSpace(line[ve - 1])) ve--;
                        spans.Add(new[] { vs, ve - vs });
                        start = i + 1;
                    }
                }
                if (idx.Max() >= spans.Count)
                    return null;
                string fmt;
                var types = ACMD_INFO.PARAM_FORMAT.TryGetValue(crc, out fmt) && fmt != null ? fmt.Split(',') : new string[0];
                return new ColorParams
                {
                    Command = ACMD_INFO.CMD_NAMES[crc], Line = line, _idx = idx, _spans = spans,
                    _float = idx.Select(i => i < types.Length && types[i].Trim() == "1").ToArray()
                };
            }

            static bool TryNumber(string s, out float v)
            {
                s = s.Trim();
                v = 0;
                bool neg = s.StartsWith("-");
                string t = neg ? s.Substring(1) : s;
                if (t.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                {
                    uint bits;
                    if (!uint.TryParse(t.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out bits))
                        return false;
                    v = bits <= 0xFFFF ? bits : BitConverter.ToSingle(BitConverter.GetBytes(bits), 0);
                }
                else if (!float.TryParse(t.TrimEnd('f', 'F'), NumberStyles.Float, CultureInfo.InvariantCulture, out v))
                    return false;
                if (neg)
                    v = -v;
                return !float.IsNaN(v) && !float.IsInfinity(v);
            }

            bool TryValues(out float[] v)
            {
                v = new float[3];
                for (int k = 0; k < 3; k++)
                {
                    var sp = _spans[_idx[k]];
                    if (!TryNumber(Line.Substring(sp[0], sp[1]), out v[k]))
                        return false;
                }
                return true;
            }

            /// <summary>0-1 values (all three at most 1 and written with a decimal point).</summary>
            bool UnitScale(float[] v)
            {
                return v.All(x => x <= 1f) && _idx.Any(i => Line.Substring(_spans[i][0], _spans[i][1]).Contains("."));
            }

            public bool TryGetColor(out Color c)
            {
                c = Color.Empty;
                float[] v;
                if (!TryValues(out v))
                    return false;
                float m = UnitScale(v) ? 255f : 1f;
                Func<float, int> b = x => Math.Max(0, Math.Min(255, (int)Math.Round(x * m)));
                c = Color.FromArgb(b(v[0]), b(v[1]), b(v[2]));
                return true;
            }

            /// <summary>The line with R, G, B set to a color, in the line's scale and number style.</summary>
            public string WithColor(Color c)
            {
                float[] v;
                bool unit = TryValues(out v) && UnitScale(v);
                var vals = new[] { c.R, c.G, c.B };
                var line = Line;
                // right to left, so the earlier spans stay valid
                foreach (var k in Enumerable.Range(0, 3).OrderByDescending(k => _spans[_idx[k]][0]))
                {
                    var sp = _spans[_idx[k]];
                    string old = Line.Substring(sp[0], sp[1]);
                    string text;
                    if (unit)
                        text = (vals[k] / 255f).ToString("0.0##", CultureInfo.InvariantCulture);
                    else if (_float[k] || old.Contains("."))
                        text = vals[k].ToString("0.0", CultureInfo.InvariantCulture);
                    else if (old.StartsWith("0x", StringComparison.OrdinalIgnoreCase) && old.Length > 6) // float bits in an int parameter
                        text = "0x" + BitConverter.ToUInt32(BitConverter.GetBytes((float)vals[k]), 0).ToString("X8");
                    else
                        text = vals[k].ToString(CultureInfo.InvariantCulture);
                    line = line.Substring(0, sp[0]) + text + line.Substring(sp[0] + sp[1]);
                }
                return line;
            }
        }

        /// <summary>Draws a color command's name in the color its R, G, B make (text in black or white,
        /// whichever reads better).</summary>
        class ColorPreviewStyle : TextStyle
        {
            public ColorPreviewStyle() : base(Brushes.Black, null, FontStyle.Bold) { }

            public override void Draw(Graphics gr, Point position, Range range)
            {
                Color c;
                var p = ColorParams.Find(range.tb.Lines[range.Start.iLine]);
                if (p != null && p.TryGetColor(out c))
                {
                    BackgroundBrush = new SolidBrush(c);
                    ForeBrush = c.R * 0.299 + c.G * 0.587 + c.B * 0.114 > 140 ? Brushes.Black : Brushes.White;
                }
                else
                {
                    BackgroundBrush = null;
                    ForeBrush = Brushes.Black;
                }
                base.Draw(gr, position, range);
                (BackgroundBrush as SolidBrush)?.Dispose();
                BackgroundBrush = null;
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