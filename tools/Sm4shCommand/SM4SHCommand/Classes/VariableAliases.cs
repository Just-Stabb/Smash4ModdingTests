using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using SALT.Moveset;

namespace Sm4shCommand.Classes
{
    /// <summary>
    /// Variable aliases: names for variable parameters, e.g. SET_FLOAT(Value=1.5, Variable=LASTHIT_HITSTUN_MUL)
    /// instead of 0x0F000052. Loaded from every .txt file in the Aliases folder next to the exe, in name
    /// order, custom.txt last (so it wins). One alias per line:
    ///     NAME = 0x0F000052          # comment
    ///     MY_FLAG = RA-Flag[13]       (any variable form works)
    /// Names are letters, digits and _ (not starting with a digit). # or // starts a comment. When
    /// "Show Variable Aliases" is on, a variable with an alias is shown by its name (the last name
    /// loaded for it); names always compile, whatever the setting.
    /// </summary>
    public static class VariableAliases
    {
        public static string Folder { get { return Path.Combine(Application.StartupPath, "Aliases"); } }

        /// <summary>Loads the folder; returns the problems found (bad lines), one per line.</summary>
        public static List<string> Load()
        {
            var problems = new List<string>();
            FighterVariable.ClearAliases();
            if (!Directory.Exists(Folder))
                return problems;
            var files = Directory.GetFiles(Folder, "*.txt", SearchOption.AllDirectories)
                .OrderBy(f => Path.GetFileName(f).Equals("custom.txt", StringComparison.OrdinalIgnoreCase) ? 1 : 0)
                .ThenBy(f => f, StringComparer.OrdinalIgnoreCase);
            foreach (var f in files)
            {
                string[] lines;
                try { lines = File.ReadAllLines(f); }
                catch (Exception) { continue; } // a file being edited or unreadable: skip it
                for (int i = 0; i < lines.Length; i++)
                {
                    var line = lines[i].Trim();
                    if (line.Length == 0 || line.StartsWith("#") || line.StartsWith("//"))
                        continue;
                    int eq = line.IndexOf('=');
                    string name = eq < 0 ? "" : line.Substring(0, eq).Trim();
                    string value = eq < 0 ? "" : line.Substring(eq + 1);
                    foreach (var mark in new[] { "#", "//" }) // comment after the value
                    {
                        int at = value.IndexOf(mark, StringComparison.Ordinal);
                        if (at >= 0)
                            value = value.Substring(0, at);
                    }
                    value = value.Trim();
                    uint raw;
                    if (!FighterVariable.IsAliasName(name) || !TryParseVariable(value, out raw) || !FighterVariable.AddAlias(name, raw))
                        problems.Add($"{Path.GetFileName(f)} line {i + 1}: \"{line}\"");
                }
            }
            return problems;
        }

        static bool TryParseVariable(string text, out uint raw)
        {
            raw = 0;
            try
            {
                if (Tooltips.TryParseValue(text, out raw))
                    return true;
                raw = new FighterVariable(text).Raw;
                return true;
            }
            catch (Exception) { return false; }
        }
    }
}
