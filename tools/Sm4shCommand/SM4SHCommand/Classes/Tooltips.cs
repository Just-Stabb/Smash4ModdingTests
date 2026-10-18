using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace Sm4shCommand.Classes
{
    /// <summary>
    /// Value tooltips: what a number written in a script means (a variable, an effect ID, an article,
    /// a special angle...). Loaded from every .txt file in the Tooltips folder next to the exe, in
    /// name order, so later files (custom.txt, which the editor's "Edit Tooltip" writes) win.
    ///
    /// File format, one entry per line:
    ///     0x1000017 = Bomb explosion | longer description (\n = new line)
    ///     361 = Sakurai angle
    /// Filters apply to the entries after them, until [any]:
    ///     [fighter kirby, captain]   only when that fighter is open (its folder name, e.g. koopa)
    ///     [command EFFECT, EFFECT_FOLLOW]   only in these commands
    ///     [param Graphic]            only in parameters with this name
    ///     [type variable]            only in parameters of this type (int, float, decimal, variable)
    ///     [index 1]                  only in the Nth parameter of the command (1 = first)
    ///     [any]                      clear the filters
    /// Lines starting with # or // are comments.
    /// </summary>
    public static class Tooltips
    {
        public class Entry
        {
            public uint Value;
            public string Name, Description, File;
            public string[] Fighters, Commands, Params, Types, Indexes;   // null = any

            public bool Matches(string fighter, string command, string param, string type, int index)
            {
                return Ok(Fighters, fighter) && Ok(Commands, command) && Ok(Params, param) && Ok(Types, type) &&
                    Ok(Indexes, index > 0 ? index.ToString(CultureInfo.InvariantCulture) : null);
            }

            static bool Ok(string[] list, string value)
            {
                return list == null || value != null && list.Any(x => x.Equals(value, StringComparison.OrdinalIgnoreCase));
            }

            // More filters = more specific = shown first.
            public int Specificity { get { return (Fighters != null ? 8 : 0) + (Commands != null ? 4 : 0) + (Params != null || Indexes != null ? 2 : 0) + (Types != null ? 1 : 0); } }
        }

        public static readonly List<Entry> Entries = new List<Entry>();
        public static string Folder { get { return Path.Combine(Application.StartupPath, "Tooltips"); } }
        public static string CustomPath { get { return Path.Combine(Folder, "custom.txt"); } }

        /// <summary>The open fighter's folder name (koopa, kirby...), or null; filters [fighter ...].</summary>
        public static string Fighter { get; set; }

        public static void Load()
        {
            Entries.Clear();
            var files = new List<string>();
            if (Directory.Exists(Folder))
                files.AddRange(Directory.GetFiles(Folder, "*.txt", SearchOption.AllDirectories)
                    .OrderBy(f => Path.GetFileName(f).Equals("custom.txt", StringComparison.OrdinalIgnoreCase) ? 1 : 0)
                    .ThenBy(f => f, StringComparer.OrdinalIgnoreCase));
            var old = Path.Combine(Application.StartupPath, "VarNames.txt"); // the earlier single file
            if (File.Exists(old))
                files.Insert(0, old);
            foreach (var f in files)
            {
                try { LoadFile(f); }
                catch (Exception) { } // a file being edited or unreadable: skip it
            }
        }

        static void LoadFile(string path)
        {
            string[] fighters = null, commands = null, @params = null, types = null, indexes = null;
            foreach (var raw in File.ReadAllLines(path))
            {
                var line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#") || line.StartsWith("//"))
                    continue;
                if (line.StartsWith("[") && line.EndsWith("]"))
                {
                    var body = line.Substring(1, line.Length - 2).Trim();
                    int sp = body.IndexOf(' ');
                    string key = (sp < 0 ? body : body.Substring(0, sp)).ToLowerInvariant();
                    string[] list = sp < 0 ? null : body.Substring(sp + 1).Split(',').Select(x => x.Trim()).Where(x => x.Length > 0).ToArray();
                    if (key == "any")
                        fighters = commands = @params = types = indexes = null;
                    else if (key == "fighter")
                        fighters = list;
                    else if (key == "command")
                        commands = list;
                    else if (key == "param")
                        @params = list;
                    else if (key == "type")
                        types = list;
                    else if (key == "index")
                        indexes = list;
                    continue;
                }
                int eq = line.IndexOf('=');
                uint value;
                if (eq <= 0 || !TryParseValue(line.Substring(0, eq).Trim(), out value))
                    continue;
                string rest = line.Substring(eq + 1);
                int bar = rest.IndexOf('|');
                Entries.Add(new Entry
                {
                    Value = value,
                    Name = (bar < 0 ? rest : rest.Substring(0, bar)).Trim(),
                    Description = bar < 0 ? "" : rest.Substring(bar + 1).Trim().Replace("\\n", "\n"),
                    File = path,
                    Fighters = fighters,
                    Commands = commands,
                    Params = @params,
                    Types = types,
                    Indexes = indexes,
                });
            }
        }

        /// <summary>0x hex or a decimal integer (negative allowed).</summary>
        public static bool TryParseValue(string text, out uint value)
        {
            text = text.Trim();
            if (text.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                return uint.TryParse(text.Substring(2), NumberStyles.HexNumber, null, out value);
            int i;
            if (int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out i))
            {
                value = unchecked((uint)i);
                return true;
            }
            value = 0;
            return false;
        }

        /// <summary>Entries for this value here, most specific first; for the same filters, the
        /// last loaded wins (so custom.txt overrides the generated files).</summary>
        public static List<Entry> Find(uint value, string command, string param, string type, int index = 0)
        {
            var found = new List<Entry>();
            for (int i = Entries.Count - 1; i >= 0; i--)
            {
                var e = Entries[i];
                if (e.Value == value && e.Matches(Fighter, command, param, type, index) &&
                    !found.Any(x => x.Specificity == e.Specificity && x.Name == e.Name))
                    found.Add(e);
            }
            return found.OrderByDescending(x => x.Specificity).ToList();
        }

        /// <summary>Tooltip text for a value, or "" if nothing is known about it.</summary>
        public static string Describe(string token, string command, string param, string type, int index = 0)
        {
            uint value;
            if (!TryParseValue(token, out value))
                return "";
            var found = Find(value, command, param, type, index);
            if (found.Count == 0)
                return "";
            var sb = new StringBuilder();
            foreach (var e in found.Take(3))
            {
                sb.Append("\n\n").Append(token).Append(": ").Append(e.Name);
                if (e.Description.Length > 0)
                    sb.Append('\n').Append(e.Description);
            }
            return sb.ToString();
        }

        /// <summary>Adds or replaces an entry in custom.txt, filtered to this command and parameter
        /// (and fighter, when one is open and fighterOnly is set).</summary>
        public static void SaveCustom(uint value, string name, string description, string command, string param, string type, bool fighterOnly, bool hex)
        {
            Directory.CreateDirectory(Folder);
            var lines = new List<string>();
            if (File.Exists(CustomPath))
                lines.AddRange(File.ReadAllLines(CustomPath));
            else
                lines.Add("# Your tooltips (Edit Tooltip in the script editor writes here). Same format as the other files.");
            string header = "[any]";
            if (fighterOnly && Fighter != null)
                header += $"\n[fighter {Fighter}]";
            if (command != null)
                header += $"\n[command {command}]";
            if (param != null)
                header += $"\n[param {param}]";
            if (type != null)
                header += $"\n[type {type}]";
            string key = hex ? $"0x{value:X}" : unchecked((int)value).ToString(CultureInfo.InvariantCulture);
            lines.Add("");
            lines.AddRange(header.Split('\n'));
            lines.Add($"{key} = {name.Replace("|", "/")}" + (description.Length > 0 ? " | " + description.Replace("\r", "").Replace("\n", "\\n") : ""));
            File.WriteAllLines(CustomPath, lines.ToArray());
            Load();
        }

        /// <summary>The fighter's folder name from an opened path: the folder after "fighter" in
        /// data/fighter/NAME/..., else null.</summary>
        public static string FighterFromPath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return null;
            var parts = path.Replace('\\', '/').Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries);
            for (int i = parts.Length - 2; i >= 0; i--)
                if (parts[i].Equals("fighter", StringComparison.OrdinalIgnoreCase))
                    return parts[i + 1].ToLowerInvariant();
            return null;
        }
    }
}
