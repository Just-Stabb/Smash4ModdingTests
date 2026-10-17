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
        }
        public ITS_EDITOR(IScript script) : this()
        {
            Script = script;
            Text = script.Deserialize();
            IsChanged = false;
        }
        public ITS_EDITOR(IScript script, string[] autocomplete) : this()
        {
            Script = script;
            Text = script.Deserialize();
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
                if (Lines[i].Trim() == want)
                    return i;
            return -1;
        }

        private void NewBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            //clear previous highlighting
            e.ChangedRange.ClearStyle(StyleIndex.All);
            //highlight tags
            e.ChangedRange.SetStyle(CommentStyle, @"//.*$", RegexOptions.Multiline);
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

        private void Editor_ToolTipNeeded(object sender, ToolTipNeededEventArgs e)
        {
            if (e.Place.iLine < 0 || e.Place.iLine >= LinesCount)
                return;
            string line = Lines[e.Place.iLine];
            int col = e.Place.iChar;

            var link = LinkAt(e.Place);
            if (link.HasValue)
            {
                e.ToolTipTitle = $"Script 0x{link.Value:X8}";
                e.ToolTipText = $"{Runtime.ScriptLabel(link.Value)}\nCtrl+click to open it.";
                return;
            }

            // The command on this line: the identifier before the first '('.
            int open = line.IndexOf('(');
            if (open < 0)
                return;
            string name = line.Substring(0, open).Trim();
            uint crc;
            if (!ACMD_INFO.TryGetIdent(name, out crc))
                return;

            string[] syntax = ACMD_INFO.PARAM_SYNTAX.ContainsKey(crc) ? ACMD_INFO.PARAM_SYNTAX[crc].Split(',') : new string[0];
            string[] types = !string.IsNullOrEmpty(ACMD_INFO.PARAM_FORMAT.ContainsKey(crc) ? ACMD_INFO.PARAM_FORMAT[crc] : null)
                ? ACMD_INFO.PARAM_FORMAT[crc].Split(',') : new string[0];
            if (types.Length == 0)
                syntax = new string[0];

            // Which parameter the mouse is over: count top-level commas before it.
            int close = line.LastIndexOf(')');
            if (col > open && (close < 0 || col <= close))
            {
                int index = 0;
                for (int i = open + 1; i < col && i < line.Length; i++)
                    if (line[i] == ',')
                        index++;
                if (index < syntax.Length)
                {
                    string pname = syntax[index];
                    e.ToolTipTitle = $"{ACMD_INFO.CMD_NAMES[crc]} \u2192 {pname}";
                    string pdesc = ACMD_INFO.GetParamDescription(crc, pname);
                    e.ToolTipText = $"Parameter {index + 1} of {syntax.Length}, {TypeName(types[index])}" +
                        (pdesc.Length > 0 ? "\n" + pdesc : "") + VariableNote(line, col);
                    return;
                }
            }

            e.ToolTipTitle = $"{ACMD_INFO.CMD_NAMES[crc]}  (0x{crc:X8})";
            string desc = ACMD_INFO.GetDescription(crc);
            string sig = syntax.Length == 0 ? "No parameters" :
                string.Join(", ", syntax.Select((s, i) => $"{s}: {TypeName(i < types.Length ? types[i] : "0")}").ToArray());
            e.ToolTipText = (desc.Length > 0 ? desc + "\n\n" : "") + sig;
        }

        // The name and description of a VarNames.txt variable written under the mouse (0x........).
        static string VariableNote(string line, int col)
        {
            int start = col, end = col;
            while (start > 0 && Uri.IsHexDigit(line[start - 1]) || start > 0 && (line[start - 1] == 'x' || line[start - 1] == 'X'))
                start--;
            while (end < line.Length && (Uri.IsHexDigit(line[end]) || line[end] == 'x' || line[end] == 'X'))
                end++;
            string word = line.Substring(start, end - start);
            uint id;
            KeyValuePair<string, string> info;
            if (word.Length < 3 || !word.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ||
                !uint.TryParse(word.Substring(2), global::System.Globalization.NumberStyles.HexNumber, null, out id) ||
                !Runtime.VarNames.TryGetValue(id, out info))
                return "";
            return $"\n\n{word}: {info.Key}" + (info.Value.Length > 0 ? "\n" + info.Value : "");
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